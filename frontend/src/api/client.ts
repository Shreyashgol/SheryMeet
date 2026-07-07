/**
 * Minimal typed fetch wrapper. The base URL comes from VITE_API_URL so the same
 * build works behind the nginx /api proxy (default) or against an absolute API
 * origin in development.
 */
const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api/v1";

export interface ApiErrorBody {
  error: { code: string; message: string; detail?: unknown };
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as ApiErrorBody;
    return new ApiError(res.status, body.error?.code ?? "error", body.error?.message ?? res.statusText);
  } catch {
    return new ApiError(res.status, "error", res.statusText);
  }
}

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { headers: { Accept: "application/json" } });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as T;
}

export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { method: "POST", body: form });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as T;
}
