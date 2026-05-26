// /v2 owns the full viewport. The shared layout.tsx provides a centered <main> with
// max-width, plus a Header and Footer. We hide those for /v2 only via a scoped global
// style block. Other routes are unaffected. We also tighten the default global form
// element padding/sizing inside /v2 only, for a denser "trading terminal" feel.
export default function V2Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <style>{`
        body > .min-h-screen > header,
        body > .min-h-screen > footer { display: none !important; }
        body > .min-h-screen > main {
          max-width: none !important;
          margin: 0 !important;
          padding: 0 !important;
        }

        /* /v2 form density — scoped to the V2 main only */
        body > .min-h-screen > main button,
        body > .min-h-screen > main .btn {
          padding: 6px 12px;
          border-radius: 6px;
          font-size: 12px;
        }
        body > .min-h-screen > main input,
        body > .min-h-screen > main select,
        body > .min-h-screen > main textarea {
          padding: 6px 9px;
          border-radius: 6px;
          font-size: 12px;
          border-width: 1px;
          border-color: rgba(255, 255, 255, 0.10);
          background: rgba(255, 255, 255, 0.04);
        }
        body > .min-h-screen > main input:focus,
        body > .min-h-screen > main select:focus,
        body > .min-h-screen > main textarea:focus {
          border-color: rgba(0, 212, 255, 0.55);
          background: rgba(0, 212, 255, 0.06);
          box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.15);
        }
        body > .min-h-screen > main button:hover:not(:disabled),
        body > .min-h-screen > main .btn:hover:not(:disabled) {
          transform: none;
        }
      `}</style>
      {children}
    </>
  );
}
