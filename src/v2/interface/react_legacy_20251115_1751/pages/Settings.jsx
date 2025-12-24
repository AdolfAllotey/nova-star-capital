import React, { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { ScrollArea } from "../components/ui/scroll-area";
import { Loader2, Save, Upload, Download, RefreshCw, CheckCircle2, AlertTriangle } from "lucide-react";

const SETTINGS_URL = "/data/settings.json";
const LS_KEY = "nova.settings.v2";

const defaultSettings = {
  email: {
    enabled: true,
    host: "",
    port: 587,
    user: "",
    password: "",
    sender: "",
    receiver: "",
    use_tls: true,
  },
  telegram: {
    enabled: true,
    bot_token: "",
    chat_id: "",
  },
  llm: {
    openai_api_key: "",
    model: "gpt-4",
  },
  scrapers: {
    telegram: true,
    twitter: true,
    reddit: true,
    telegram_limit: 100,
    twitter_limit: 100,
    reddit_limit: 100,
  },
};

function deepMerge(base, incoming) {
  const out = { ...base };
  for (const k of Object.keys(incoming || {})) {
    if (incoming[k] && typeof incoming[k] === "object" && !Array.isArray(incoming[k])) {
      out[k] = deepMerge(base[k] || {}, incoming[k]);
    } else {
      out[k] = incoming[k];
    }
  }
  return out;
}

export default function Settings() {
  const [loading, setLoading] = useState(true);
  const [saveBusy, setSaveBusy] = useState(false);
  const [info, setInfo] = useState("");
  const [warn, setWarn] = useState("");
  const [settings, setSettings] = useState(defaultSettings);
  const fileRef = useRef(null);

  // charger defaults + localStorage
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setInfo("");
      setWarn("");
      try {
        // localStorage d’abord
        const fromLS = (() => {
          try {
            const raw = localStorage.getItem(LS_KEY);
            return raw ? JSON.parse(raw) : null;
          } catch {
            return null;
          }
        })();

        // puis settings.json (optionnel)
        let fromFile = null;
        try {
          const res = await fetch(`${SETTINGS_URL}?ts=${Date.now()}`);
          if (res.ok) fromFile = await res.json();
        } catch {
          // silencieux: le fichier peut ne pas exister
        }

        if (!cancelled) {
          const merged = deepMerge(defaultSettings, deepMerge(fromFile || {}, fromLS || {}));
          setSettings(merged);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // helpers d’UI
  const setField = (path, value) => {
    setSettings((prev) => {
      const parts = path.split(".");
      const next = { ...prev };
      let cur = next;
      for (let i = 0; i < parts.length - 1; i++) {
        const p = parts[i];
        cur[p] = { ...(cur[p] || {}) };
        cur = cur[p];
      }
      cur[parts[parts.length - 1]] = value;
      return next;
    });
  };

  const validEmail = useMemo(() => {
    if (!settings.email.enabled) return true;
    const { host, port, user, sender, receiver } = settings.email;
    return Boolean(host && port && user && sender && receiver);
  }, [settings.email]);

  const validTelegram = useMemo(() => {
    if (!settings.telegram.enabled) return true;
    const { bot_token, chat_id } = settings.telegram;
    return Boolean(bot_token && chat_id);
  }, [settings.telegram]);

  const save = async () => {
    setSaveBusy(true);
    setInfo("");
    setWarn("");
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(settings));
      setInfo("Paramètres sauvegardés dans le navigateur (localStorage).");
    } catch (e) {
      console.error(e);
      setWarn("Échec de la sauvegarde locale.");
    } finally {
      setSaveBusy(false);
    }
  };

  const exportJSON = () => {
    try {
      const blob = new Blob([JSON.stringify(settings, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "settings.export.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setInfo("Export effectué (settings.export.json).");
    } catch (e) {
      console.error(e);
      setWarn("Échec de l’export.");
    }
  };

  const importJSON = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const json = JSON.parse(reader.result);
        setSettings((prev) => deepMerge(prev, json));
        setInfo("Import effectué.");
      } catch (e) {
        console.error(e);
        setWarn("Fichier invalide.");
      }
    };
    reader.readAsText(file);
  };

  const testConfig = (kind) => {
    setInfo("");
    setWarn("");
    if (kind === "email") {
      if (!validEmail) return setWarn("Config email incomplète.");
      setInfo("Test email (à blanc) OK — vérifie côté backend via le pipeline.");
    }
    if (kind === "telegram") {
      if (!validTelegram) return setWarn("Config Telegram incomplète.");
      setInfo("Test Telegram (à blanc) OK — envoi réel via le pipeline / script Python.");
    }
    if (kind === "llm") {
      if (!settings.llm.openai_api_key) return setWarn("Clé OpenAI manquante.");
      setInfo("Test LLM (à blanc) OK.");
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">Settings</h1>
          <p className="text-sm text-muted-foreground">Configuration des intégrations et préférences.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => window.location.reload()} disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
            Recharger
          </Button>
          <Button onClick={save} disabled={saveBusy}>
            {saveBusy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            Sauvegarder
          </Button>
        </div>
      </div>

      {(info || warn) && (
        <div
          className={
            "flex items-center gap-2 px-3 py-2 rounded-md border " +
            (warn
              ? "bg-amber-50 border-amber-200 text-amber-800"
              : "bg-emerald-50 border-emerald-200 text-emerald-800")
          }
        >
          {warn ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
          <span className="text-sm">{warn || info}</span>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {/* Email */}
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Email (SMTP)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="email-enabled">Activer</Label>
              <Switch id="email-enabled" checked={settings.email.enabled}
                onCheckedChange={(v) => setField("email.enabled", v)} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <Label>Host</Label>
                <Input
                  placeholder="smtp.exemple.com"
                  value={settings.email.host}
                  onChange={(e) => setField("email.host", e.target.value)}
                />
              </div>
              <div>
                <Label>Port</Label>
                <Input
                  type="number"
                  value={settings.email.port}
                  onChange={(e) => setField("email.port", Number(e.target.value || 0))}
                />
              </div>
              <div>
                <Label>Utilisateur</Label>
                <Input
                  placeholder="user@exemple.com"
                  value={settings.email.user}
                  onChange={(e) => setField("email.user", e.target.value)}
                />
              </div>
              <div>
                <Label>Mot de passe</Label>
                <Input
                  type="password"
                  value={settings.email.password}
                  onChange={(e) => setField("email.password", e.target.value)}
                />
              </div>
              <div>
                <Label>Sender</Label>
                <Input
                  placeholder="expediteur@exemple.com"
                  value={settings.email.sender}
                  onChange={(e) => setField("email.sender", e.target.value)}
                />
              </div>
              <div>
                <Label>Receiver</Label>
                <Input
                  placeholder="destinataire@exemple.com"
                  value={settings.email.receiver}
                  onChange={(e) => setField("email.receiver", e.target.value)}
                />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="email-tls">TLS</Label>
              <Switch id="email-tls" checked={settings.email.use_tls}
                onCheckedChange={(v) => setField("email.use_tls", v)} />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => testConfig("email")} disabled={!settings.email.enabled || !validEmail}>
                Tester (à blanc)
              </Button>
              <Button variant="secondary" onClick={exportJSON}>
                <Download className="w-4 h-4 mr-2" /> Exporter JSON
              </Button>
              <input
                ref={fileRef}
                type="file"
                accept="application/json"
                className="hidden"
                onChange={(e) => importJSON(e.target.files?.[0])}
              />
              <Button variant="secondary" onClick={() => fileRef.current?.click()}>
                <Upload className="w-4 h-4 mr-2" /> Importer JSON
              </Button>
            </div>
            {!validEmail && <p className="text-xs text-amber-700">Configuration email incomplète.</p>}
          </CardContent>
        </Card>

        {/* Telegram */}
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Telegram</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="tg-enabled">Activer</Label>
              <Switch id="tg-enabled" checked={settings.telegram.enabled}
                onCheckedChange={(v) => setField("telegram.enabled", v)} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="md:col-span-2">
                <Label>Bot Token</Label>
                <Input
                  type="password"
                  placeholder="123456:ABC-DEF..."
                  value={settings.telegram.bot_token}
                  onChange={(e) => setField("telegram.bot_token", e.target.value)}
                />
              </div>
              <div>
                <Label>Chat ID</Label>
                <Input
                  placeholder="5308497197"
                  value={settings.telegram.chat_id}
                  onChange={(e) => setField("telegram.chat_id", e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => testConfig("telegram")} disabled={!settings.telegram.enabled || !validTelegram}>
                Tester (à blanc)
              </Button>
              <Button onClick={save} disabled={saveBusy}>
                {saveBusy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                Sauvegarder
              </Button>
            </div>
            {!validTelegram && <p className="text-xs text-amber-700">Configuration Telegram incomplète.</p>}
          </CardContent>
        </Card>

        {/* LLM */}
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">LLM</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="md:col-span-2">
                <Label>OpenAI API Key</Label>
                <Input
                  type="password"
                  placeholder="sk-..."
                  value={settings.llm.openai_api_key}
                  onChange={(e) => setField("llm.openai_api_key", e.target.value)}
                />
              </div>
              <div>
                <Label>Model</Label>
                <Input
                  placeholder="gpt-4"
                  value={settings.llm.model}
                  onChange={(e) => setField("llm.model", e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => testConfig("llm")}>Tester (à blanc)</Button>
              <Button onClick={save} disabled={saveBusy}>
                {saveBusy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                Sauvegarder
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Scrapers */}
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Scrapers</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="flex items-center justify-between border rounded-md px-3 py-2">
                <span>Telegram</span>
                <Switch
                  checked={settings.scrapers.telegram}
                  onCheckedChange={(v) => setField("scrapers.telegram", v)}
                />
              </div>
              <div className="flex items-center justify-between border rounded-md px-3 py-2">
                <span>Twitter</span>
                <Switch
                  checked={settings.scrapers.twitter}
                  onCheckedChange={(v) => setField("scrapers.twitter", v)}
                />
              </div>
              <div className="flex items-center justify-between border rounded-md px-3 py-2">
                <span>Reddit</span>
                <Switch
                  checked={settings.scrapers.reddit}
                  onCheckedChange={(v) => setField("scrapers.reddit", v)}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <Label>Telegram limit</Label>
                <Input
                  type="number"
                  value={settings.scrapers.telegram_limit}
                  onChange={(e) => setField("scrapers.telegram_limit", Number(e.target.value || 0))}
                />
              </div>
              <div>
                <Label>Twitter limit</Label>
                <Input
                  type="number"
                  value={settings.scrapers.twitter_limit}
                  onChange={(e) => setField("scrapers.twitter_limit", Number(e.target.value || 0))}
                />
              </div>
              <div>
                <Label>Reddit limit</Label>
                <Input
                  type="number"
                  value={settings.scrapers.reddit_limit}
                  onChange={(e) => setField("scrapers.reddit_limit", Number(e.target.value || 0))}
                />
              </div>
            </div>

            <div className="flex gap-2">
              <Button onClick={save} disabled={saveBusy}>
                {saveBusy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                Sauvegarder
              </Button>
              <Button variant="secondary" onClick={exportJSON}>
                <Download className="w-4 h-4 mr-2" /> Exporter JSON
              </Button>
              <input
                ref={fileRef}
                type="file"
                accept="application/json"
                className="hidden"
                onChange={(e) => importJSON(e.target.files?.[0])}
              />
              <Button variant="secondary" onClick={() => fileRef.current?.click()}>
                <Upload className="w-4 h-4 mr-2" /> Importer JSON
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Source JSON vue rapide */}
      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Aperçu JSON</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-56 w-full rounded-md border p-3 bg-muted/30">
            <pre className="text-xs leading-relaxed">{JSON.stringify(settings, null, 2)}</pre>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}