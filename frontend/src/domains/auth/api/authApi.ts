import { apiClient } from "@/shared/lib/apiClient";
import type { APIResponse } from "@/shared/types/api.types";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export const authApi = {
  register: async (data: RegisterRequest): Promise<UserProfile> => {
    const res = await apiClient.post<APIResponse<UserProfile>>("/auth/register", data);
    return res.data.data;
  },
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const res = await apiClient.post<APIResponse<TokenResponse>>("/auth/login", data);
    return res.data.data;
  },
  refresh: async (refreshToken: string): Promise<TokenResponse> => {
    const res = await apiClient.post<APIResponse<TokenResponse>>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return res.data.data;
  },
  getOAuthProviders: async (): Promise<Record<"google" | "github", boolean>> => {
    const res = await apiClient.get<APIResponse<Record<"google" | "github", boolean>>>("/auth/oauth/providers");
    return res.data.data;
  },
  getMe: async (): Promise<UserProfile> => {
    const res = await apiClient.get<APIResponse<UserProfile>>("/auth/me");
    return res.data.data;
  },
  updateProfile: async (data: { full_name?: string }): Promise<UserProfile> => {
    const res = await apiClient.patch<APIResponse<UserProfile>>("/auth/me", data);
    return res.data.data;
  },
  changePassword: async (data: { current_password: string; new_password: string }): Promise<TokenResponse> => {
    const res = await apiClient.post<APIResponse<TokenResponse>>("/auth/me/change-password", data);
    return res.data.data;
  },
  listUsers: async (): Promise<UserProfile[]> => {
    const res = await apiClient.get<APIResponse<UserProfile[]>>("/auth/users");
    return res.data.data;
  },
  updateUser: async ({ id, ...data }: { id: string; role?: UserProfile["role"]; is_active?: boolean }): Promise<UserProfile> => {
    const res = await apiClient.patch<APIResponse<UserProfile>>(`/auth/users/${id}`, data);
    return res.data.data;
  },
};
