import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { tokenStorage } from "@/shared/lib/tokenStorage";

const BASE_URL = "/api/v1";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccess();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface NormalizedApiError {
  status: number;
  errorCode: string;
  message: string;
  details: Record<string, unknown>;
}

// One refresh at a time: if several requests 401 together (the dashboard
// polls a few endpoints in parallel), they all wait on the same refresh
// instead of each burning the refresh token.
let refreshInFlight: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refreshToken = tokenStorage.getRefresh();
  if (!refreshToken) throw new Error("No refresh token");
  // Plain axios, not apiClient, so this call can't recurse into the interceptor.
  const res = await axios.post(`${BASE_URL}/auth/refresh`, { refresh_token: refreshToken });
  tokenStorage.set(res.data.data);
  return res.data.data.access_token;
}

const NO_REFRESH_PATHS = ["/auth/login", "/auth/register", "/auth/refresh"];

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ error_code?: string; message?: string; details?: Record<string, unknown> }>) => {
    const original = error.config as RetriableConfig | undefined;
    const isAuthEndpoint = NO_REFRESH_PATHS.some((p) => original?.url?.endsWith(p));

    if (error.response?.status === 401 && original && !original._retried && !isAuthEndpoint) {
      original._retried = true;
      try {
        refreshInFlight ??= refreshAccessToken().finally(() => {
          refreshInFlight = null;
        });
        const newToken = await refreshInFlight;
        original.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(original);
      } catch {
        // Refresh token expired or revoked — the session is over.
        tokenStorage.clear();
      }
    }

    const normalized: NormalizedApiError = {
      status: error.response?.status ?? 0,
      errorCode: error.response?.data?.error_code ?? "NETWORK_ERROR",
      message: error.response?.data?.message ?? "Unable to reach the server. Please try again.",
      details: error.response?.data?.details ?? {},
    };
    return Promise.reject(normalized);
  }
);
