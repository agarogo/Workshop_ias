import { NextRequest, NextResponse } from 'next/server'

type RouteContext = {
  params: Promise<{ path?: string[] }>
}

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const BACKEND_URL = process.env.EXPERIMENTS_BACKEND_URL ?? 'http://localhost:8100'

type JsonObject = Record<string, unknown>

function json(value: unknown, init?: ResponseInit) {
  return NextResponse.json(value, init)
}

function backendUrl(path: string, searchParams?: URLSearchParams) {
  const base = BACKEND_URL.replace(/\/$/, '')
  const url = new URL(`${base}${path.startsWith('/') ? path : `/${path}`}`)

  searchParams?.forEach((value, key) => {
    url.searchParams.set(key, value)
  })

  return url
}

async function backendJson<T>(
  path: string,
  init?: RequestInit,
  searchParams?: URLSearchParams,
): Promise<T> {
  const response = await fetch(backendUrl(path, searchParams), {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    cache: 'no-store',
  })

  if (!response.ok) {
    const details = await response.text()
    throw new Error(`BenchMerge ${response.status}: ${details || response.statusText}`)
  }

  return (await response.json()) as T
}

function asArray<T = JsonObject>(value: unknown): T[] {
  if (Array.isArray(value)) return value as T[]
  if (value && typeof value === 'object' && Array.isArray((value as JsonObject).items)) {
    return (value as { items: T[] }).items
  }
  return []
}

function pickString(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback
}

function normalizeTest(test: JsonObject) {
  return {
    id: pickString(test.id ?? test.test_id),
    input: pickString(test.input ?? test.user_prompt ?? test.name),
    checks: test.checks && typeof test.checks === 'object' ? test.checks : {},
    tags: Array.isArray(test.tags) ? test.tags : [],
    runtime_params:
      test.runtime_params && typeof test.runtime_params === 'object'
        ? test.runtime_params
        : {},
  }
}

function getUserPromptFromRequestPayload(payload: unknown) {
  if (!payload || typeof payload !== 'object') return ''

  const messages = (payload as JsonObject).messages
  if (!Array.isArray(messages)) return ''

  const userMessage = [...messages]
    .reverse()
    .find((message) => {
      return (
        message &&
        typeof message === 'object' &&
        (message as JsonObject).role === 'user'
      )
    })

  if (!userMessage || typeof userMessage !== 'object') return ''
  return pickString((userMessage as JsonObject).content)
}

function normalizeResult(result: JsonObject, fallbackRunId: string) {
  return {
    experiment_run_id: pickString(result.experiment_run_id ?? result.run_id, fallbackRunId),
    test_id: pickString(result.test_id),
    config_name: pickString(result.config_name ?? result.config_id),
    model_name: pickString(result.model_name ?? result.model) || null,
    input_text:
      pickString(result.input_text) ||
      getUserPromptFromRequestPayload(result.request_payload) ||
      pickString(result.test_name),
    response_text: pickString(result.response_text),
    score: Number(result.score ?? 0),
    passed: Boolean(result.passed),
    latency_ms: Number(result.latency_ms ?? 0),
    timestamp_utc: pickString(result.timestamp_utc ?? result.created_at),
    thread_id: pickString(result.thread_id) || null,
    trace_id: pickString(result.trace_id) || null,
    runtime_params:
      result.runtime_params && typeof result.runtime_params === 'object'
        ? result.runtime_params
        : {},
    raw_response: result.raw_response ?? result.response_payload ?? null,
    scoring: result.scoring ?? null,
  }
}

async function loadConfigs() {
  return asArray<JsonObject>(await backendJson<unknown>('/configs'))
}

async function loadTests() {
  return asArray<JsonObject>(await backendJson<unknown>('/tests'))
}

async function loadRuns() {
  return asArray<JsonObject>(await backendJson<unknown>('/runs'))
}

async function loadRunBundle(runId: string) {
  return backendJson<JsonObject>(`/runs/${encodeURIComponent(runId)}`)
}

async function resolveConfigIds(selectedNames: unknown) {
  const names = Array.isArray(selectedNames) ? selectedNames.map(String) : []
  if (names.length === 0) return []

  const configs = await loadConfigs()
  return names
    .map((name) => {
      const config = configs.find((item) => {
        return item.id === name || item.config_id === name || item.name === name
      })
      return pickString(config?.id ?? config?.config_id, name)
    })
    .filter(Boolean)
}

async function proxyToBenchMerge(request: NextRequest, path: string[]) {
  const targetPath = `/${path.map(encodeURIComponent).join('/')}`
  const response = await fetch(backendUrl(targetPath, request.nextUrl.searchParams), {
    method: request.method,
    headers: { 'Content-Type': 'application/json' },
    body: request.method === 'GET' ? undefined : await request.text(),
    cache: 'no-store',
  })

  return new NextResponse(await response.text(), {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') ?? 'application/json',
    },
  })
}

export async function GET(request: NextRequest, context: RouteContext) {
  const { path = [] } = await context.params

  try {
    if (path[0] === 'catalog') {
      const [configs, tests] = await Promise.all([loadConfigs(), loadTests()])
      const configNames = configs
        .map((config) => pickString(config.name ?? config.id ?? config.config_id))
        .filter(Boolean)
      const models = [
        ...new Set(configs.map((config) => pickString(config.model)).filter(Boolean)),
      ]

      return json({
        datasets: ['benchfile://default'],
        configs: configNames,
        tests: tests.map((test) => pickString(test.id ?? test.test_id)).filter(Boolean),
        models,
      })
    }

    if (path[0] === 'tests' && path.length === 1) {
      const tests = await loadTests()
      return json(tests.map(normalizeTest))
    }

    if (path[0] === 'configs' && path.length === 1) {
      return json(await loadConfigs())
    }

    if (path[0] === 'runs' && path.length === 1) {
      const runs = await loadRuns()
      return json(
        runs.map((run) => ({
          run_id: pickString(run.run_id),
          files: [],
        })),
      )
    }

    if (path[0] === 'runs' && path[1] && path.length === 2) {
      const runId = path[1]
      const bundle = await loadRunBundle(runId)
      const results = asArray<JsonObject>(bundle.results)
      const configs: Record<string, string[]> = {}

      for (const result of results) {
        const configName = pickString(result.config_name ?? result.config_id, 'unknown_config')
        const resultId = pickString(result.id ?? result.result_id)
        const fileName = resultId ? `${resultId}.json` : `${pickString(result.test_id)}.json`
        configs[configName] = [...(configs[configName] ?? []), fileName]
      }

      return json({
        run_id: runId,
        manifest:
          bundle.run && typeof bundle.run === 'object'
            ? bundle.run
            : {},
        configs,
      })
    }

    if (path[0] === 'runs' && path[1] && path[2] === 'files' && path[3] && path[4]) {
      const runId = path[1]
      const configName = decodeURIComponent(path[3])
      const fileName = decodeURIComponent(path[4]).replace(/\.json$/, '')
      const bundle = await loadRunBundle(runId)
      const results = asArray<JsonObject>(bundle.results)
      const result = results.find((item) => {
        const itemConfigName = pickString(item.config_name ?? item.config_id)
        const itemFile = pickString(item.id ?? item.result_id)
        return itemConfigName === configName && itemFile === fileName
      })

      if (!result) {
        return json({ detail: 'Result file not found' }, { status: 404 })
      }

      return json(normalizeResult(result, runId))
    }

    if (path[0] === 'jobs' && path[1]) {
      const jobId = path[1]
      const runId = jobId.startsWith('benchfile_') ? jobId.slice('benchfile_'.length) : jobId
      return json({
        job_id: jobId,
        status: 'completed',
        experiment_run_id: runId,
        error: null,
        result: { run_id: runId },
      })
    }

    if (path[0] === 'files') {
      return proxyToBenchMerge(request, path)
    }

    return proxyToBenchMerge(request, path)
  } catch (error) {
    return json(
      { detail: error instanceof Error ? error.message : String(error) },
      { status: 500 },
    )
  }
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path = [] } = await context.params

  try {
    if (path[0] === 'tests') {
      const body = (await request.json()) as JsonObject
      const payload = {
        test_id: pickString(body.id ?? body.test_id),
        name: pickString(body.name ?? body.id ?? body.test_id, 'Untitled test'),
        user_prompt: pickString(body.input ?? body.user_prompt),
        checks: body.checks && typeof body.checks === 'object' ? body.checks : {},
        tags: Array.isArray(body.tags) ? body.tags : [],
      }

      const created = await backendJson<JsonObject>('/tests', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      return json(normalizeTest(created))
    }

    if (path[0] === 'run') {
      const body = (await request.json()) as JsonObject
      const configIds = await resolveConfigIds(
        body.selected_config_names ?? body.config_ids ?? body.selected_config_ids,
      )

      const payload = {
        selected_test_ids: Array.isArray(body.selected_test_ids)
          ? body.selected_test_ids.map(String)
          : [],
        config_ids: configIds,
      }

      const run = await backendJson<JsonObject>('/runs', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      const runId = pickString(run.run_id)
      return json({
        job_id: `benchfile_${runId}`,
        status: 'queued',
        experiment_run_id: runId,
        result: run,
      })
    }

    return proxyToBenchMerge(request, path)
  } catch (error) {
    return json(
      { detail: error instanceof Error ? error.message : String(error) },
      { status: 500 },
    )
  }
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxyToBenchMerge(request, (await context.params).path ?? [])
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxyToBenchMerge(request, (await context.params).path ?? [])
}
