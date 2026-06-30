"use client";

import { motion } from "framer-motion";

export function GuardrailNotice({ message }: { message: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="bg-[#FFF0F1] border border-[#FECDD3] rounded-2xl p-5"
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-base">🛡️</span>
        <span className="text-sm font-semibold text-[#9F1239]">
          안전 계층 작동
        </span>
        <span className="text-xs bg-[#FECDD3] text-[#9F1239] px-2 py-0.5 rounded-full font-medium ml-auto">
          가드레일
        </span>
      </div>
      <p className="text-sm text-[#881337] leading-relaxed">{message}</p>
    </motion.div>
  );
}
