import { useMemo, useState } from 'react';
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Badge,
  BarChart,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  DataTable,
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  useAnalyticsQuery,
} from '@databricks/appkit-ui/react';
import { sql } from '@databricks/appkit-ui/js';
import { AlertCircle, CheckCircle2, ClipboardList, FileText, Gauge, Scale } from 'lucide-react';

const CATEGORIAS = [
  'Todas',
  'Engenharia de Dados & Lakehouse',
  'Arquitetura Cloud & Infraestrutura',
  'Produto & Discovery de Cliente',
  'Governança, Segurança & FinOps',
  'Operações, SRE & Qualidade',
  'Alinhamento & Gestão de Equipe',
];

const PRIORIDADES = ['Todas', 'Alta', 'Média', 'Baixa'];

export function AnalyticsPage() {
  const [categoria, setCategoria] = useState<string>('Todas');
  const [prioridade, setPrioridade] = useState<string>('Todas');

  const kpisQuery = useAnalyticsQuery('kpis_resumo', {});
  const evalQuery = useAnalyticsQuery('metricas_avaliacao', {});

  const catalogoParams = useMemo(() => ({ categoria: sql.string(categoria) }), [categoria]);
  const actionItemsParams = useMemo(() => ({ prioridade: sql.string(prioridade) }), [prioridade]);
  const emptyParams = useMemo(() => ({}), []);

  const kpiRow = kpisQuery.data?.[0];
  const geralEval = evalQuery.data?.find((r) => r.categoria_metrica.startsWith('Geral'));

  return (
    <div className="space-y-6 w-full max-w-7xl mx-auto pb-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-foreground">
            Painel Gold — Reuniões, Decisões, Pendências e Avaliação da POC
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Dados ao vivo do SQL Warehouse sobre{' '}
            <code>workspace.dev_vitortesteestudos_meeting_intelligence_poc</code>
          </p>
        </div>
        {kpiRow?.ultima_atualizacao && (
          <Badge variant="outline">
            Último processamento Gold: {kpiRow.ultima_atualizacao.slice(0, 19).replace('T', ' ')} UTC
          </Badge>
        )}
      </div>

      {/* KPI Error State */}
      {kpisQuery.error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erro ao consultar KPIs na camada Gold</AlertTitle>
          <AlertDescription>{kpisQuery.error}</AlertDescription>
        </Alert>
      )}

      {/* Top KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="inline-flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5" /> Reuniões Processadas
            </CardDescription>
            <CardTitle className="text-3xl font-bold">
              {kpisQuery.loading ? (
                <Skeleton className="h-8 w-20" />
              ) : (
                Number(kpiRow?.total_reunioes ?? 0)
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {kpisQuery.loading ? (
              <Skeleton className="h-4 w-36" />
            ) : (
              <>
                JSON válido: <strong>{Number(kpiRow?.taxa_json_valido_pct ?? 0).toFixed(1)}%</strong>{' '}
                · Fonte: <code>gold_transcricoes_catalogo</code>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="inline-flex items-center gap-1.5">
              <Scale className="h-3.5 w-3.5" /> Decisões &amp; Pendências
            </CardDescription>
            <CardTitle className="text-3xl font-bold">
              {kpisQuery.loading ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                `${Number(kpiRow?.total_decisoes ?? 0)} / ${Number(kpiRow?.total_pendencias ?? 0)}`
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            Decisões aprovadas / Bloqueios abertos · Fontes: <code>gold_decisoes</code> &amp;{' '}
            <code>gold_pendencias</code>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="inline-flex items-center gap-1.5">
              <ClipboardList className="h-3.5 w-3.5" /> Action Items Extraídos
            </CardDescription>
            <CardTitle className="text-3xl font-bold">
              {kpisQuery.loading ? (
                <Skeleton className="h-8 w-20" />
              ) : (
                Number(kpiRow?.total_action_items ?? 0)
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            Com dono, prazo e prioridade · Fonte: <code>gold_action_items</code>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="inline-flex items-center gap-1.5">
              <Gauge className="h-3.5 w-3.5" /> Qualidade F1 &amp; Custo POC
            </CardDescription>
            <CardTitle className="text-3xl font-bold">
              {evalQuery.loading ? (
                <Skeleton className="h-8 w-24" />
              ) : geralEval ? (
                `${Number(geralEval.f1_pct).toFixed(1)}%`
              ) : (
                '—'
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {evalQuery.loading ? (
              <Skeleton className="h-4 w-40" />
            ) : geralEval ? (
              <>
                Custo médio: <strong>${Number(geralEval.custo_medio_reuniao_usd).toFixed(5)}</strong>{' '}
                / reunião · ${Number(geralEval.custo_projecao_1000_usd).toFixed(2)}/1k
              </>
            ) : (
              'Execute evaluate_poc.py para popular métricas'
            )}
          </CardContent>
        </Card>
      </div>

      {/* Category Distribution BarChart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            Volume de Decisões, Pendências e Action Items por Categoria Temática
          </CardTitle>
          <CardDescription>
            Distribuição consolidada das entidades extraídas via <code>ai_query</code> +{' '}
            <code>responseFormat</code> nas 18 transcrições processadas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <BarChart
            queryKey="reunioes_por_categoria"
            parameters={emptyParams}
            xKey="categoria_ia"
            yKey={['decisoes', 'pendencias', 'action_items']}
            colorPalette="categorical"
            showLegend
            height={320}
          />
        </CardContent>
      </Card>

      {/* Gold Tables Explorer Tabs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Explorar Tabelas Gold &amp; Avaliação Quantitativa</CardTitle>
          <CardDescription>
            Filtre, ordene e inspecione os registros governados diretamente do Unity Catalog.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="action_items" className="w-full">
            <TabsList className="flex flex-wrap h-auto gap-1 mb-5">
              <TabsTrigger value="action_items">Action Items</TabsTrigger>
              <TabsTrigger value="catalogo">Catálogo de Reuniões</TabsTrigger>
              <TabsTrigger value="decisoes">Decisões</TabsTrigger>
              <TabsTrigger value="pendencias">Pendências</TabsTrigger>
              <TabsTrigger value="avaliacao">Avaliação POC (Gabarito)</TabsTrigger>
            </TabsList>

            {/* TAB: ACTION ITEMS */}
            <TabsContent value="action_items" className="space-y-4">
              <div className="max-w-xs space-y-1.5">
                <Label htmlFor="filtro-prioridade">Filtrar por prioridade</Label>
                <Select value={prioridade} onValueChange={setPrioridade}>
                  <SelectTrigger id="filtro-prioridade">
                    <SelectValue placeholder="Todas as prioridades" />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORIDADES.map((p) => (
                      <SelectItem key={p} value={p}>
                        {p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <DataTable
                queryKey="action_items_lista"
                parameters={actionItemsParams}
                filterColumn="responsavel"
                filterPlaceholder="Filtrar por responsável..."
                pageSize={10}
              />
            </TabsContent>

            {/* TAB: CATÁLOGO */}
            <TabsContent value="catalogo" className="space-y-4">
              <div className="max-w-md space-y-1.5">
                <Label htmlFor="filtro-categoria">Filtrar por categoria temática</Label>
                <Select value={categoria} onValueChange={setCategoria}>
                  <SelectTrigger id="filtro-categoria">
                    <SelectValue placeholder="Todas as categorias" />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIAS.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <DataTable
                queryKey="catalogo_reunioes"
                parameters={catalogoParams}
                filterColumn="titulo"
                filterPlaceholder="Buscar por título da reunião..."
                pageSize={10}
              />
            </TabsContent>

            {/* TAB: DECISÕES */}
            <TabsContent value="decisoes">
              <DataTable
                queryKey="decisoes_lista"
                parameters={emptyParams}
                filterColumn="decisao"
                filterPlaceholder="Buscar nas decisões aprovadas..."
                pageSize={10}
              />
            </TabsContent>

            {/* TAB: PENDÊNCIAS */}
            <TabsContent value="pendencias">
              <DataTable
                queryKey="pendencias_lista"
                parameters={emptyParams}
                filterColumn="descricao"
                filterPlaceholder="Buscar nas pendências/bloqueios..."
                pageSize={10}
              />
            </TabsContent>

            {/* TAB: AVALIAÇÃO QUANTITATIVA */}
            <TabsContent value="avaliacao" className="space-y-4">
              {evalQuery.loading && (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              )}
              {evalQuery.error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Erro ao carregar métricas de avaliação</AlertTitle>
                  <AlertDescription>{evalQuery.error}</AlertDescription>
                </Alert>
              )}
              {!evalQuery.loading && !evalQuery.error && (!evalQuery.data || evalQuery.data.length === 0) && (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>Nenhuma avaliação registrada</EmptyTitle>
                    <EmptyDescription>
                      Execute <code>databricks/eval/evaluate_poc.py</code> para popular{' '}
                      <code>gold_metricas_avaliacao</code>.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
              {!evalQuery.loading && evalQuery.data && evalQuery.data.length > 0 && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="secondary" className="inline-flex items-center gap-1">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Modelo: {evalQuery.data[0].modelo_llm}
                    </Badge>
                    <Badge variant="outline">
                      Gabarito: {Number(evalQuery.data[0].total_transcricoes_gabarito)} de{' '}
                      {Number(evalQuery.data[0].total_transcricoes_volume)} transcrições
                    </Badge>
                    <Badge variant="outline">
                      Latência p50: {Number(evalQuery.data[0].latencia_p50_seg).toFixed(2)}s · p95:{' '}
                      {Number(evalQuery.data[0].latencia_p95_seg).toFixed(2)}s
                    </Badge>
                  </div>

                  <div className="rounded-lg border border-border overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Dimensão Avaliada</TableHead>
                          <TableHead className="text-right">TP</TableHead>
                          <TableHead className="text-right">FP</TableHead>
                          <TableHead className="text-right">FN</TableHead>
                          <TableHead className="text-right">Precisão</TableHead>
                          <TableHead className="text-right">Recall</TableHead>
                          <TableHead className="text-right">F1-Score</TableHead>
                          <TableHead className="text-right">JSON Válido</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {evalQuery.data.map((row) => (
                          <TableRow key={row.categoria_metrica}>
                            <TableCell className="font-medium">{row.categoria_metrica}</TableCell>
                            <TableCell className="text-right">{Number(row.tp)}</TableCell>
                            <TableCell className="text-right">{Number(row.fp)}</TableCell>
                            <TableCell className="text-right">{Number(row.fn)}</TableCell>
                            <TableCell className="text-right font-medium">
                              {Number(row.precisao_pct).toFixed(1)}%
                            </TableCell>
                            <TableCell className="text-right font-medium">
                              {Number(row.recall_pct).toFixed(1)}%
                            </TableCell>
                            <TableCell className="text-right font-semibold">
                              {Number(row.f1_pct).toFixed(1)}%
                            </TableCell>
                            <TableCell className="text-right">
                              {Number(row.taxa_json_valido_pct).toFixed(1)}%
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
