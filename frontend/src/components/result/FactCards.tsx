import { factKind } from "@/lib/types";
import type { Fact, LookupFact, ChangeFact, SumFact } from "@/lib/types";
import { FinancialCard } from "./FinancialCard";
import { ChangeCard } from "./ChangeCard";
import { SumCard } from "./SumCard";

export function FactCards({ facts }: { facts: Fact[] }) {
  if (facts.length === 0) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {facts.map((fact, i) => {
        const kind = factKind(fact);
        if (kind === "sum")    return <SumCard    key={i} fact={fact as SumFact} />;
        if (kind === "change") return <ChangeCard key={i} fact={fact as ChangeFact} />;
        return <FinancialCard key={i} fact={fact as LookupFact} />;
      })}
    </div>
  );
}
