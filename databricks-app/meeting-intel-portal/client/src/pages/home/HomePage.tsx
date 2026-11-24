import { Link } from 'react-router';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Separator,
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
} from '@databricks/appkit-ui/react';
import {
  ArrowRight,
  BarChart3,
  Building2,
  CheckCircle2,
  CloudUpload,
  Database,
  FileText,
  GraduationCap,
  Layers,
  Lock,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
} from 'lucide-react';

export function HomePage() {
  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-8">
      {/* Hero Banner */}
      <Card className="border-border bg-card shadow-sm overflow-hidden">
        <CardContent className="p-6 sm:p-8 space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="inline-flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5" />
              Portal Corporativo Databricks Apps
            </Badge>
            <Badge variant="outline">Lakeflow SDP • ai_query + responseFormat • Genie Space</Badge>
          </div>

          <div className="space-y-2 max-w-4xl">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Transforme transcrições de reuniões em decisões, pendências e planos de ação governados
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
              Este portal corporativo centraliza o ciclo completo da POC{' '}
              <strong className="text-foreground">Meeting &amp; Video Intelligence</strong> no
              Databricks Lakehouse: upload de transcrições no Unity Catalog Volume, processamento
              Medalhão com parsing determinístico de falantes e extração estruturada via{' '}
              <code>ai_query</code> + <code>responseFormat</code>, painel analítico das tabelas
              Gold, métricas de avaliação e chat em linguagem natural no{' '}
              <strong className="text-foreground">Genie Space</strong>.
            </p>
          </div>

          <div className="flex flex-wrap gap-3 pt-1">
            <Button asChild>
              <Link to="/analytics">
                <BarChart3 className="h-4 w-4 mr-2" />
                Explorar Painel Gold &amp; Métricas
                <ArrowRight className="h-4 w-4 ml-2" />
              </Link>
            </Button>
            <Button variant="secondary" asChild>
              <Link to="/genie">
                <MessageSquareText className="h-4 w-4 mr-2" />
                Perguntar ao Genie AI
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/files">
                <CloudUpload className="h-4 w-4 mr-2" />
                Subir Transcrição no Volume UC
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 3 Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <div className="w-9 h-9 rounded-lg bg-muted text-foreground flex items-center justify-center mb-2">
              <CloudUpload className="h-4 w-4" />
            </div>
            <CardTitle className="text-base">1. Ingestão Governada no Volume UC</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground leading-relaxed">
            Envie arquivos <code>.vtt</code> (Microsoft Teams), <code>.srt</code> (Zoom/Whisper),{' '}
            <code>.txt</code> (Google Meet) ou <code>.json</code> pela aba{' '}
            <strong className="text-foreground">Upload &amp; Volume</strong>. A camada Bronze lê
            incrementalmente com <code>STREAM read_files(...)</code>.
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="w-9 h-9 rounded-lg bg-muted text-foreground flex items-center justify-center mb-2">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <CardTitle className="text-base">2. Operação Empresarial &amp; LGPD</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground leading-relaxed">
            Acesso via <strong className="text-foreground">SSO corporativo</strong> com controle de
            acesso nativo no Unity Catalog (RBAC). Para reuniões ultraconfidenciais ou vídeos{' '}
            <code>.mp4</code> &gt; 1h sem legenda, combine com o utilitário local 100% offline.
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="w-9 h-9 rounded-lg bg-muted text-foreground flex items-center justify-center mb-2">
              <Database className="h-4 w-4" />
            </div>
            <CardTitle className="text-base">3. Tabelas Gold + Genie Space</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground leading-relaxed">
            Consulte decisões, bloqueios/pendências, action items com dono/prazo e métricas de
            qualidade (precisão, recall, latência, custo) tanto nos dashboards quanto via perguntas
            em português no <strong className="text-foreground">Genie AI</strong>.
          </CardContent>
        </Card>
      </div>

      {/* Interactive Tutorial & Enterprise Guide Tabs */}
      <Card>
        <CardHeader>
          <CardTitle>Tutorial de Uso &amp; Guia Empresarial</CardTitle>
          <CardDescription>
            Selecione uma aba abaixo para entender o passo a passo operacional, as diretrizes de
            segurança em ambiente empresarial e a arquitetura Medalhão da POC.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="quickstart" className="w-full">
            <TabsList className="flex flex-wrap h-auto gap-1 mb-6">
              <TabsTrigger value="quickstart" className="inline-flex items-center gap-1.5">
                <GraduationCap className="h-4 w-4" />
                Tutorial Passo a Passo
              </TabsTrigger>
              <TabsTrigger value="enterprise" className="inline-flex items-center gap-1.5">
                <Building2 className="h-4 w-4" />
                Uso em Ambiente Empresarial
              </TabsTrigger>
              <TabsTrigger value="architecture" className="inline-flex items-center gap-1.5">
                <Workflow className="h-4 w-4" />
                Arquitetura Medalhão &amp; POC
              </TabsTrigger>
            </TabsList>

            {/* TAB 1: QUICKSTART */}
            <TabsContent value="quickstart" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="bg-muted/30">
                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-2">
                      <Badge>Passo 1</Badge>
                      <CardTitle className="text-base">Subir a transcrição no Volume UC</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground space-y-2">
                    <p>
                      Acesse a aba <strong className="text-foreground">Upload &amp; Volume</strong>{' '}
                      e clique em <strong className="text-foreground">Enviar Transcrição</strong>{' '}
                      para subir arquivos <code>.vtt</code> (Teams), <code>.srt</code> (Zoom) ou{' '}
                      <code>.txt</code> (Meet).
                    </p>
                    <p>
                      Os arquivos ficam salvos no Volume governado{' '}
                      <code>raw_transcripts</code> no Unity Catalog, prontos para ingestão
                      incremental.
                    </p>
                  </CardContent>
                </Card>

                <Card className="bg-muted/30">
                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-2">
                      <Badge>Passo 2</Badge>
                      <CardTitle className="text-base">Execução da Pipeline Medalhão</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground space-y-2">
                    <p>
                      A pipeline Lakeflow Serverless processa automaticamente apenas arquivos novos:
                      Bronze ingere via <code>read_files</code>, Silver limpa e extrai falantes e
                      metadados, e Gold executa <code>ai_query</code> com{' '}
                      <code>responseFormat</code> JSON Schema estrito.
                    </p>
                  </CardContent>
                </Card>

                <Card className="bg-muted/30">
                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-2">
                      <Badge>Passo 3</Badge>
                      <CardTitle className="text-base">Analisar no Painel Gold</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground space-y-2">
                    <p>
                      Na aba <strong className="text-foreground">Painel Gold</strong>, acompanhe os
                      KPIs consolidados, filtre o catálogo de reuniões por categoria temática,
                      priorize <strong className="text-foreground">Action Items</strong> por
                      criticidade e revise todas as decisões e bloqueios em aberto.
                    </p>
                  </CardContent>
                </Card>

                <Card className="bg-muted/30">
                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-2">
                      <Badge>Passo 4</Badge>
                      <CardTitle className="text-base">Consultar em Linguagem Natural no Genie</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground space-y-2">
                    <p>
                      Na aba <strong className="text-foreground">Genie AI</strong>, faça perguntas
                      em português como{' '}
                      <em>
                        &ldquo;Quais action items de prioridade Alta estão pendentes?&rdquo;
                      </em>{' '}
                      e inspecione sempre o SQL gerado antes de compartilhar com a liderança.
                    </p>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* TAB 2: ENTERPRISE USAGE */}
            <TabsContent value="enterprise" className="space-y-6">
              <div className="space-y-2">
                <h3 className="text-base font-semibold text-foreground">
                  Matriz de Confidencialidade e Arquitetura Híbrida na Empresa
                </h3>
                <p className="text-sm text-muted-foreground">
                  Use esta política para decidir quando operar diretamente neste{' '}
                  <strong className="text-foreground">Databricks App corporativo</strong> e quando
                  combinar com o utilitário local offline do repositório.
                </p>
              </div>

              <div className="rounded-lg border border-border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Classificação da Reunião</TableHead>
                      <TableHead>Canal / Ferramenta Recomendada</TableHead>
                      <TableHead>Controles de Segurança &amp; Governança</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell className="font-medium">
                        <Badge variant="destructive" className="inline-flex items-center gap-1">
                          <Lock className="h-3 w-3" /> Altamente Confidencial (M&amp;A, RH, LGPD)
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        App Local 100% Offline (<code>faster-whisper</code> + <code>Ollama</code>)
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        Processamento estritamente local na máquina/VPC privada. Nenhum dado sai
                        para APIs externas; arquivos temporários apagados ao fim do job.
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-medium">
                        <Badge variant="secondary" className="inline-flex items-center gap-1">
                          <ShieldCheck className="h-3 w-3" /> Interno Corporativo (Padrão)
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        <strong>Este Databricks App</strong> + Unity Catalog Volume + Lakeflow SDP +
                        Genie Space
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        SSO da empresa (Entra ID/Okta), RBAC por grupo no Unity Catalog, execução
                        OBO no Genie, trilha de auditoria (<code>system.access.audit</code>) e
                        endpoints Foundation Model dentro do tenant Databricks.
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-medium">
                        <Badge variant="outline">Gravações Longas (.mp4 &gt; 1h) / YouTube</Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        Pré-processamento Local (<code>ffmpeg</code> + chunking 20 min) → Upload do{' '}
                        <code>.srt/.vtt</code> aqui
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        Evita limites de upload/timeout de containers web e envia para o Lakehouse
                        apenas a transcrição leve e já sincronizada com timestamps.
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>

              <Separator />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="bg-muted/20">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base inline-flex items-center gap-2">
                      <Users className="h-4 w-4 text-primary" />
                      Fluxo com Teams, SharePoint, Zoom e Meet
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground space-y-2">
                    <ul className="list-disc pl-5 space-y-1.5">
                      <li>
                        <strong className="text-foreground">Microsoft Teams / Stream:</strong> baixe
                        o arquivo <code>.vtt</code> da aba <em>Transcrição</em> — a camada Silver
                        extrai automaticamente cada falante a partir das tags{' '}
                        <code>&lt;v Nome&gt;</code>.
                      </li>
                      <li>
                        <strong className="text-foreground">Zoom / Whisper:</strong> suba o{' '}
                        <code>.srt</code> com prefixo <code>Nome Sobrenome: fala</code>; o parser
                        preserva o autor em cada turno.
                      </li>
                      <li>
                        <strong className="text-foreground">Google Meet / Atas TXT:</strong> inclua
                        cabeçalho <code>Reunião:</code> e <code>Data: YYYY-MM-DD</code> ou prefixe o
                        nome do arquivo com a data para indexação cronológica automática.
                      </li>
                    </ul>
                  </CardContent>
                </Card>

                <Card className="bg-muted/20">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base inline-flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-primary" />
                      Boas Práticas de Governança &amp; Adoção
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground space-y-2">
                    <ul className="list-disc pl-5 space-y-1.5">
                      <li>
                        <strong className="text-foreground">Privilégio Mínimo (RBAC):</strong>{' '}
                        segregue Volumes e tabelas Gold por diretoria ou use Row-Level Security /
                        Column Masks para PII (CPF, e-mail, salários).
                      </li>
                      <li>
                        <strong className="text-foreground">Zero Segredos no Código:</strong>{' '}
                        recursos (SQL Warehouse, Volume, Genie Space) são injetados via{' '}
                        <code>app.yaml</code> (<code>valueFrom</code>) e permissões gerenciadas pelo
                        Databricks Apps.
                      </li>
                      <li>
                        <strong className="text-foreground">Revisão Humana (HITL):</strong> trate
                        decisões e action items extraídos por LLM como acelerador — valide donos,
                        prazos e o SQL gerado no Genie antes de decisões críticas.
                      </li>
                      <li>
                        <strong className="text-foreground">Avaliação Contínua:</strong> mantenha um
                        gabarito manual sempre que trocar prompt ou modelo LLM e monitore precisão,
                        recall, JSON válido, latência e custo na aba{' '}
                        <strong className="text-foreground">Painel Gold</strong>.
                      </li>
                    </ul>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* TAB 3: ARCHITECTURE */}
            <TabsContent value="architecture" className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <Card className="bg-muted/20">
                  <CardHeader className="pb-2">
                    <CardDescription className="uppercase text-xs font-semibold inline-flex items-center gap-1.5">
                      <CloudUpload className="h-3.5 w-3.5" /> Landing (Volume UC)
                    </CardDescription>
                    <CardTitle className="text-sm">raw_transcripts</CardTitle>
                  </CardHeader>
                  <CardContent className="text-xs text-muted-foreground leading-relaxed">
                    Armazena transcrições brutas (<code>.vtt</code>, <code>.srt</code>,{' '}
                    <code>.txt</code>, <code>.json</code>) com governança Unity Catalog e controle
                    de versão/auditoria.
                  </CardContent>
                </Card>

                <Card className="bg-muted/20">
                  <CardHeader className="pb-2">
                    <CardDescription className="uppercase text-xs font-semibold inline-flex items-center gap-1.5">
                      <Layers className="h-3.5 w-3.5" /> Bronze (read_files)
                    </CardDescription>
                    <CardTitle className="text-sm">bronze_transcricoes_raw</CardTitle>
                  </CardHeader>
                  <CardContent className="text-xs text-muted-foreground leading-relaxed">
                    Streaming Table com <code>STREAM read_files(..., wholeText =&gt; true)</code>,
                    hash SHA-256 por caminho e metadados de ingestão incremental.
                  </CardContent>
                </Card>

                <Card className="bg-muted/20">
                  <CardHeader className="pb-2">
                    <CardDescription className="uppercase text-xs font-semibold inline-flex items-center gap-1.5">
                      <FileText className="h-3.5 w-3.5" /> Silver (Parsing)
                    </CardDescription>
                    <CardTitle className="text-sm">silver_transcricoes_limpas</CardTitle>
                  </CardHeader>
                  <CardContent className="text-xs text-muted-foreground leading-relaxed">
                    Limpeza determinística sem LLM + extração de <strong>falantes</strong>, turnos,
                    data da reunião, formato, duração e estimativa de tokens (100% acurácia no
                    gabarito).
                  </CardContent>
                </Card>

                <Card className="bg-muted/20">
                  <CardHeader className="pb-2">
                    <CardDescription className="uppercase text-xs font-semibold inline-flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5" /> Gold (ai_query + Genie)
                    </CardDescription>
                    <CardTitle className="text-sm">5 Tabelas Gold + Genie</CardTitle>
                  </CardHeader>
                  <CardContent className="text-xs text-muted-foreground leading-relaxed">
                    <code>ai_query</code> + <code>responseFormat</code> JSON Schema estrito (1x por
                    reunião) populando <code>catalogo</code>, <code>decisoes</code>,{' '}
                    <code>pendencias</code>, <code>action_items</code> e{' '}
                    <code>metricas_avaliacao</code>.
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
