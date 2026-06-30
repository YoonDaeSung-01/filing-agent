"use client";

import { useMutation } from "@tanstack/react-query";
import { ask } from "@/lib/api";
import type { AskRequest, AskResponse } from "@/lib/types";

export function useAsk() {
  return useMutation<AskResponse, Error, AskRequest>({
    mutationFn: ask,
  });
}
