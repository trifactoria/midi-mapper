// components/types.ts

export type Port = { id: number; name: string };

export type ContextHeader = {
  daw_slot: number;
  preset_slot: number;
  port_id: number;
  channel: number;
  bank_msb: number;
  bank_lsb: number;
  program: number;
};

export type Binding = {
  id: number;
  context_id: number;
  enabled: number;
  trig_type: number;
  note: number | null;
  cc: number | null;
  command: string;
  debounce_ms: number;
  require_armed: number;
};
