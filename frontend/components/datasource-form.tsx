"use client";

import { ArrowLeftIcon, CheckCircleIcon, CircleNotchIcon, ShieldCheckIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { useDatasources } from "@/components/datasource-provider";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FormField, SelectField } from "@/components/ui/form-field";
import { ApiClientError } from "@/lib/api-client";
import {
  createDatasource,
  testDatasourceConnection,
  type DatasourceCreateInput,
  type SslMode,
} from "@/lib/datasources";

const presets: Record<DatasourceCreateInput["source_type"], DatasourceCreateInput> = {
  postgresql: {
  name: "Docker demo PostgreSQL store",
  source_type: "postgresql",
  host: "demo-postgres",
  port: 5432,
  database: "insightmesh_demo",
  username: "demo_reader",
  password: "",
  ssl_mode: "disable",
  allowed_schemas: ["public"],
  },
  mysql: {
    name: "Docker demo MySQL store",
    source_type: "mysql",
    host: "demo-mysql",
    port: 3306,
    database: "insightmesh_demo",
    username: "demo_reader",
    password: "",
    ssl_mode: "disable",
    allowed_schemas: ["insightmesh_demo"],
  },
};

const initialValues = presets.postgresql;

function fingerprint(values: DatasourceCreateInput) {
  return JSON.stringify(values);
}

function errorMessage(reason: unknown) {
  if (reason instanceof ApiClientError) return reason.message;
  return "InsightMesh could not complete the connection request.";
}

export function DatasourceForm() {
  const router = useRouter();
  const { refresh } = useDatasources();
  const [values, setValues] = useState(initialValues);
  const [testedFingerprint, setTestedFingerprint] = useState<string | null>(null);
  const [testSummary, setTestSummary] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"idle" | "testing" | "saving">("idle");
  const errorRef = useRef<HTMLDivElement>(null);
  const tested = testedFingerprint === fingerprint(values);

  useEffect(() => {
    if (error) errorRef.current?.focus();
  }, [error]);

  function setField<K extends keyof DatasourceCreateInput>(key: K, value: DatasourceCreateInput[K]) {
    setValues((current) => ({ ...current, [key]: value }));
    setTestSummary(null);
    setError(null);
  }

  async function handleTest() {
    setMode("testing");
    setError(null);
    try {
      const connection = {
        source_type: values.source_type,
        host: values.host,
        port: values.port,
        database: values.database,
        username: values.username,
        password: values.password,
        ssl_mode: values.ssl_mode,
        allowed_schemas: values.allowed_schemas,
      };
      const result = await testDatasourceConnection(connection);
      setTestedFingerprint(fingerprint(values));
      const engine = values.source_type === "mysql" ? "MySQL" : "PostgreSQL";
      setTestSummary(`Connected to ${result.database}. ${engine} ${result.server_version}. Read-only transaction confirmed.`);
    } catch (reason) {
      setTestedFingerprint(null);
      setError(errorMessage(reason));
    } finally {
      setMode("idle");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tested) {
      setError("Test this unchanged connection before saving it.");
      return;
    }
    setMode("saving");
    setError(null);
    try {
      const source = await createDatasource(values);
      await refresh();
      router.push(`/sources/${source.id}`);
    } catch (reason) {
      setError(errorMessage(reason));
      setMode("idle");
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Link href="/sources" className="inline-flex min-h-11 items-center gap-2 rounded-md text-sm font-semibold text-primary hover:text-primary-hover">
        <ArrowLeftIcon size={18} aria-hidden /> Back to sources
      </Link>
      <PageHeader eyebrow="Datasource onboarding" title="Add SQL source" description="Choose PostgreSQL or MySQL, test access, then save encrypted credentials and discover metadata." />
      <form onSubmit={handleSubmit} className="space-y-5">
        {error ? (
          <div ref={errorRef} tabIndex={-1} role="alert" className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
            <p className="font-semibold">Connection could not be completed</p><p className="mt-1">{error}</p>
          </div>
        ) : null}
        {testSummary ? (
          <div role="status" className="flex items-start gap-2 rounded-lg border border-green-700/30 bg-green-50 p-4 text-sm text-green-900">
            <CheckCircleIcon className="mt-0.5 shrink-0" size={19} weight="fill" aria-hidden /><div><p className="font-semibold">Connection test passed</p><p className="mt-1">{testSummary}</p></div>
          </div>
        ) : null}
        <Card className="p-5 sm:p-6">
          <div className="mb-5 flex items-start gap-3 border-b border-border pb-5">
            <span className="grid size-10 shrink-0 place-items-center rounded-md bg-muted text-primary"><ShieldCheckIcon size={21} aria-hidden /></span>
            <div><h2 className="font-semibold text-text">Read-only connection</h2><p className="mt-1 text-sm text-muted-foreground">Use a database account with SELECT-only permissions. Passwords are encrypted and never returned by the API.</p></div>
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <SelectField label="Database engine" name="source_type" value={values.source_type} onChange={(event) => {
              const sourceType = event.target.value as DatasourceCreateInput["source_type"];
              setValues({ ...presets[sourceType], password: values.password });
              setTestedFingerprint(null);
              setTestSummary(null);
              setError(null);
            }}>
              <option value="postgresql">PostgreSQL</option><option value="mysql">MySQL 8+</option>
            </SelectField>
            <FormField label="Connection name" name="name" required value={values.name} onChange={(event) => setField("name", event.target.value)} />
            <FormField label="Host" name="host" required value={values.host} onChange={(event) => setField("host", event.target.value)} hint={`Use ${values.source_type === "mysql" ? "demo-mysql" : "demo-postgres"} for the Docker demo.`} />
            <FormField label="Port" name="port" type="number" min={1} max={65535} required value={values.port} onChange={(event) => setField("port", Number(event.target.value))} />
            <FormField label="Database" name="database" required value={values.database} onChange={(event) => setField("database", event.target.value)} />
            <FormField label="Username" name="username" autoComplete="username" required value={values.username} onChange={(event) => setField("username", event.target.value)} />
            <FormField label="Password" name="password" type="password" autoComplete="new-password" required value={values.password} onChange={(event) => setField("password", event.target.value)} hint="For the demo, use DEMO_READER_PASSWORD from your local .env." />
            <SelectField label="SSL mode" name="ssl_mode" value={values.ssl_mode} onChange={(event) => setField("ssl_mode", event.target.value as SslMode)}>
              <option value="disable">Disable (local Docker only)</option><option value="prefer">Prefer</option><option value="require">Require</option>{values.source_type === "postgresql" ? <><option value="verify-ca">Verify CA</option><option value="verify-full">Verify full</option></> : null}
            </SelectField>
            <FormField label={values.source_type === "mysql" ? "Allowed databases" : "Allowed schemas"} name="allowed_schemas" required value={values.allowed_schemas.join(", ")} onChange={(event) => setField("allowed_schemas", event.target.value.split(",").map((item) => item.trim()).filter(Boolean))} hint={`Comma-separated ${values.source_type === "mysql" ? "MySQL databases" : "PostgreSQL schemas"}. Queries outside this list are blocked.`} />
          </div>
        </Card>
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button asChild variant="ghost"><Link href="/sources">Cancel</Link></Button>
          <Button type="button" variant="secondary" onClick={() => void handleTest()} disabled={mode !== "idle"}>
            {mode === "testing" ? <CircleNotchIcon className="animate-spin" size={18} aria-hidden /> : null}{mode === "testing" ? "Testing…" : "Test connection"}
          </Button>
          <Button type="submit" disabled={!tested || mode !== "idle"}>
            {mode === "saving" ? <CircleNotchIcon className="animate-spin" size={18} aria-hidden /> : null}{mode === "saving" ? "Saving and discovering…" : "Save connection"}
          </Button>
        </div>
      </form>
    </div>
  );
}
