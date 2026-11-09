import { useSyncExternalStore } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi, type UserProfile } from "@/domains/auth/api/authApi";
import { tokenStorage } from "@/shared/lib/tokenStorage";

function subscribeToSignOut(onChange: () => void) {
  window.addEventListener(tokenStorage.SIGNED_OUT_EVENT, onChange);
  // "storage" fires when another tab logs in or out.
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(tokenStorage.SIGNED_OUT_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** Re-renders the caller the moment tokens are cleared, from anywhere. */
export function useHasToken() {
  return useSyncExternalStore(subscribeToSignOut, () => !!tokenStorage.getAccess());
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.getMe,
    retry: false,
    staleTime: 60_000,
    enabled: !!tokenStorage.getAccess(),
  });
}

export function useHasRole(...roles: UserProfile["role"][]) {
  const { data: user } = useCurrentUser();
  return !!user && roles.includes(user.role);
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.login,
    onSuccess: (tokens) => {
      tokenStorage.set(tokens);
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

export function useOAuthProviders() {
  return useQuery({
    queryKey: ["auth", "oauth-providers"],
    queryFn: authApi.getOAuthProviders,
    staleTime: 5 * 60_000,
    retry: false,
  });
}

/** Stores tokens handed back by a Google/GitHub sign-in and loads the user. */
export function useAcceptTokens() {
  const queryClient = useQueryClient();
  return (tokens: { access_token: string; refresh_token: string }) => {
    tokenStorage.set(tokens);
    queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
  };
}

export function useRegister() {
  return useMutation({
    mutationFn: authApi.register,
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return {
    logout: () => {
      // Drop every cached query so the next user never sees the previous
      // user's detections, not just their profile.
      queryClient.clear();
      tokenStorage.clear();
    },
  };
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.updateProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

export function useUsers(enabled: boolean) {
  return useQuery({ queryKey: ["auth", "users"], queryFn: authApi.listUsers, enabled });
}

export function useAdminUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.updateUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["auth", "users"] }),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: authApi.changePassword,
    // The backend revokes all old tokens on password change and hands back
    // a fresh pair, so this session stays signed in.
    onSuccess: (tokens) => tokenStorage.set(tokens),
  });
}
