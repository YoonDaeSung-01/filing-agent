"use client";

import { useCallback, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchMe, loginAccount, registerAccount } from "@/lib/api";
import { clearToken, getToken, setToken } from "@/lib/auth";

export function useAuth() {
  const [token, setTokenState] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const qc = useQueryClient();

  useEffect(() => {
    setTokenState(getToken());
    setHydrated(true);
  }, []);

  const me = useQuery({
    queryKey: ["auth-me", token],
    queryFn: fetchMe,
    enabled: hydrated && !!token,
    retry: false,
  });

  // 토큰은 유효한데 /auth/me 가 401 등으로 실패하면(만료·위조) 로그아웃 처리
  useEffect(() => {
    if (me.isError && token) {
      clearToken();
      setTokenState(null);
    }
  }, [me.isError, token]);

  const afterAuth = useCallback(
    (t: string) => {
      setToken(t);
      setTokenState(t);
      qc.invalidateQueries({ queryKey: ["auth-me"] });
      qc.invalidateQueries({ queryKey: ["watchlist-db"] });
      qc.invalidateQueries({ queryKey: ["journal-db"] });
    },
    [qc],
  );

  const loginMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      loginAccount(username, password),
    onSuccess: (res) => afterAuth(res.access_token),
  });

  const registerMutation = useMutation({
    mutationFn: ({
      username,
      name,
      password,
    }: {
      username: string;
      name: string;
      password: string;
    }) => registerAccount(username, name, password),
    onSuccess: (res) => afterAuth(res.access_token),
  });

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
    qc.invalidateQueries({ queryKey: ["watchlist-db"] });
    qc.invalidateQueries({ queryKey: ["journal-db"] });
  }, [qc]);

  return {
    isAuthenticated: hydrated && !!token && !me.isError,
    username: me.data?.username,
    name: me.data?.name,
    isLoading: !hydrated || (!!token && me.isLoading),
    login: loginMutation.mutate,
    isLoggingIn: loginMutation.isPending,
    loginError: loginMutation.error,
    register: registerMutation.mutate,
    isRegistering: registerMutation.isPending,
    registerError: registerMutation.error,
    logout,
  };
}
