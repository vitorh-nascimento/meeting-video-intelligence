import { useEffect, useState } from 'react';
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  GenieChat,
} from '@databricks/appkit-ui/react';
import { Info, ShieldCheck, Sparkles, UserCheck } from 'lucide-react';

interface WhoAmIResponse {
  email: string | null;
  user: string | null;
  executionMode: 'obo' | 'sp';
  genieSpaceConfigured: boolean;
}

const SAMPLE_PROMPTS = [
  'Quais action items de prioridade Alta estão pendentes e quem são os responsáveis?',
  'Quantas reuniões, decisões, pendências e action items foram processados por categoria?',
  'Quais pendências e bloqueios estão em aberto nas reuniões de Governança, Segurança e FinOps?',
  'Qual foi a precisão, recall, taxa de JSON válido, latência média e custo estimado da POC?',
];

export function GeniePage() {
  const [me, setMe] = useState<WhoAmIResponse | null>(null);

  useEffect(() => {
    fetch('/api/whoami')
      .then((res) => (res.ok ? res.json() : null))
      .then((data: WhoAmIResponse | null) => {
        if (data) setMe(data);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-5 w-full max-w-6xl mx-auto pb-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-foreground inline-flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Genie AI — Consultas em Linguagem Natural sobre as Reuniões
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Conectado ao Genie Space <strong>Meeting &amp; Video Intelligence POC</strong> (5
            tabelas Gold: catálogo, decisões, pendências, action items e métricas de avaliação).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="inline-flex items-center gap-1.5">
            <UserCheck className="h-3.5 w-3.5" />
            {me?.email ?? me?.user ?? 'Autenticado'}
          </Badge>
          <Badge variant="outline" className="inline-flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5" />
            OBO (escopo dashboards.genie)
          </Badge>
        </div>
      </div>

      {/* Governance & AI Disclaimer */}
      <Alert>
        <Info className="h-4 w-4" />
        <AlertTitle>Transparência e Governança de IA</AlertTitle>
        <AlertDescription>
          As perguntas executam via Databricks Genie sob suas permissões de acesso no Unity Catalog
          (escopo <code>dashboards.genie</code>). Respostas geradas por IA podem conter
          imprecisões — clique em <strong>SQL gerado</strong> dentro de cada resposta do chat para
          inspecionar a consulta exata antes de tomar decisões.
        </AlertDescription>
      </Alert>

      {/* Main Chat Container with explicit height */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 h-[min(640px,70vh)] border border-border rounded-lg overflow-hidden bg-card shadow-xs">
          <GenieChat
            alias="default"
            placeholder="Pergunte sobre decisões, pendências, action items ou métricas da POC..."
          />
        </div>

        <Card className="h-fit">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Sugestões de Perguntas</CardTitle>
            <CardDescription>
              Copie e envie no chat para explorar rapidamente as tabelas Gold:
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {SAMPLE_PROMPTS.map((q) => (
              <div
                key={q}
                className="rounded-md border border-border bg-muted/40 p-2.5 text-xs text-foreground leading-relaxed"
              >
                {q}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
