import { useState, useEffect } from "react";
import AppHeader from "@/components/AppHeader";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { toast } from "@/hooks/use-toast";

type TimePeriod = "7" | "30" | "90" | "all";

interface UserPreferences {
  defaultTimePeriod: TimePeriod;
  notifications: {
    newSignals: boolean;
    statusChanges: boolean;
    weeklyDigest: boolean;
    highScoreAlerts: boolean;
  };
  display: {
    compactView: boolean;
    showDismissed: boolean;
  };
}

const DEFAULT_PREFS: UserPreferences = {
  defaultTimePeriod: "90",
  notifications: {
    newSignals: true,
    statusChanges: true,
    weeklyDigest: false,
    highScoreAlerts: true,
  },
  display: {
    compactView: false,
    showDismissed: true,
  },
};

const loadPrefs = (): UserPreferences => {
  try {
    const raw = localStorage.getItem("user_preferences");
    return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
};

const TIME_OPTIONS: { value: TimePeriod; label: string }[] = [
  { value: "7", label: "7 days" },
  { value: "30", label: "30 days" },
  { value: "90", label: "90 days" },
  { value: "all", label: "All time" },
];

const Settings = () => {
  const [prefs, setPrefs] = useState<UserPreferences>(loadPrefs);

  useEffect(() => {
    localStorage.setItem("user_preferences", JSON.stringify(prefs));
  }, [prefs]);

  const updateNotif = (key: keyof UserPreferences["notifications"], val: boolean) => {
    setPrefs((p) => ({ ...p, notifications: { ...p.notifications, [key]: val } }));
  };

  const updateDisplay = (key: keyof UserPreferences["display"], val: boolean) => {
    setPrefs((p) => ({ ...p, display: { ...p.display, [key]: val } }));
  };

  const handleReset = () => {
    setPrefs(DEFAULT_PREFS);
    toast({ title: "Preferences reset", description: "All settings restored to defaults." });
  };

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <div className="max-w-2xl mx-auto px-4 py-8">
        <h1 className="text-lg font-semibold text-foreground mb-1">Settings</h1>
        <p className="text-sm text-muted-foreground mb-8">
          Manage your dashboard preferences and notification settings.
        </p>

        {/* Default Time Period */}
        <Section title="Default Time Period" description="Choose the default date range for analytics charts.">
          <div className="flex flex-wrap gap-2">
            {TIME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setPrefs((p) => ({ ...p, defaultTimePeriod: opt.value }))}
                className={`text-xs px-4 py-2 rounded-md border font-medium transition-colors ${
                  prefs.defaultTimePeriod === opt.value
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-card text-muted-foreground border-border hover:bg-secondary hover:text-foreground"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </Section>

        {/* Notifications */}
        <Section title="Notifications" description="Control which alerts and updates you receive.">
          <div className="space-y-4">
            <ToggleRow
              label="New signal alerts"
              description="Get notified when new buying signals are detected."
              checked={prefs.notifications.newSignals}
              onChange={(v) => updateNotif("newSignals", v)}
            />
            <ToggleRow
              label="Status change alerts"
              description="Notify when a company's status is updated."
              checked={prefs.notifications.statusChanges}
              onChange={(v) => updateNotif("statusChanges", v)}
            />
            <ToggleRow
              label="Weekly digest"
              description="Receive a weekly summary of top opportunities."
              checked={prefs.notifications.weeklyDigest}
              onChange={(v) => updateNotif("weeklyDigest", v)}
            />
            <ToggleRow
              label="High score alerts"
              description="Alert when a company score exceeds 80."
              checked={prefs.notifications.highScoreAlerts}
              onChange={(v) => updateNotif("highScoreAlerts", v)}
            />
          </div>
        </Section>

        {/* Display */}
        <Section title="Display" description="Customize how data appears on your dashboard.">
          <div className="space-y-4">
            <ToggleRow
              label="Compact view"
              description="Use denser table rows on the dashboard."
              checked={prefs.display.compactView}
              onChange={(v) => updateDisplay("compactView", v)}
            />
            <ToggleRow
              label="Show dismissed companies"
              description="Include dismissed companies in the main table."
              checked={prefs.display.showDismissed}
              onChange={(v) => updateDisplay("showDismissed", v)}
            />
          </div>
        </Section>

        {/* Reset */}
        <div className="mt-8 pt-6 border-t flex justify-end">
          <button
            onClick={handleReset}
            className="text-xs px-4 py-2 rounded-md border border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground transition-colors font-medium"
          >
            Reset to Defaults
          </button>
        </div>
      </div>
    </div>
  );
};

const Section = ({ title, description, children }: { title: string; description: string; children: React.ReactNode }) => (
  <div className="mb-8">
    <h2 className="text-sm font-semibold text-foreground mb-0.5">{title}</h2>
    <p className="text-xs text-muted-foreground mb-4">{description}</p>
    {children}
  </div>
);

const ToggleRow = ({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) => (
  <div className="flex items-center justify-between gap-4">
    <div>
      <Label className="text-sm font-medium text-foreground">{label}</Label>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
    <Switch checked={checked} onCheckedChange={onChange} />
  </div>
);

export default Settings;
