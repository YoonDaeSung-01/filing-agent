"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export function SourcePanel({ sources }: { sources: string[] }) {
  if (sources.length === 0) return null;

  return (
    <Accordion multiple={false}>
      <AccordionItem value="sources" className="border-0">
        <AccordionTrigger className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider hover:text-[#3182F6] hover:no-underline py-2 px-0">
          출처 보기 ({sources.length}건)
        </AccordionTrigger>
        <AccordionContent className="pt-2 pb-0">
          <ul className="space-y-1.5">
            {sources.map((src, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-xs text-[#6B7280] bg-[#F2F4F6] px-3 py-2 rounded-xl"
              >
                <span className="text-[#3182F6] font-bold shrink-0">{i + 1}</span>
                <span>{src}</span>
              </li>
            ))}
          </ul>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
