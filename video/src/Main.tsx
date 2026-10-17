import React from 'react';
import {AbsoluteFill, Audio, Easing, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// Paleta y tipografía de la app real (static/styles.css).
const C = {
  blue: '#2C5F8A', blueDark: '#1e4464', indigo: '#667eea', violet: '#764ba2', light: '#F5F5F5', ink: '#1b2733',
  gray: '#666666', green: '#1f8f4e', greenBg: '#e8f5ec', greenInk: '#1d5b33', amberBg: '#fff4d6', amberInk: '#7a5300',
  red: '#e05252', white: '#ffffff',
};
const FONT = 'Inter, "Inter Display", "Noto Color Emoji", system-ui, sans-serif';
const MONO = '"DejaVu Sans Mono", ui-monospace, monospace';

// Duraciones por escena (30 fps).
const D = {hook: 120, reveal: 105, product: 510, how: 270, proof: 270, built: 135, outro: 120};
export const TOTAL = D.hook + D.reveal + D.product + D.how + D.proof + D.built + D.outro;

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

const Appear: React.FC<{at: number; dist?: number; len?: number; style?: React.CSSProperties; children: React.ReactNode}> = ({
  at, dist = 28, len = 14, style, children,
}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [at, at + len], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  return <div style={{opacity: p, transform: `translateY(${(1 - p) * dist}px)`, ...style}}>{children}</div>;
};

// Fundido de entrada y salida pasando por el fondo (sin doble exposición).
const Scene: React.FC<{dur: number; children: React.ReactNode}> = ({dur, children}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 10, dur - 10, dur], [0, 1, 1, 0], clamp);
  return <AbsoluteFill style={{opacity: o, fontFamily: FONT}}>{children}</AbsoluteFill>;
};

const Background: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 30;
  const x = 28 + 8 * Math.sin(t / 5);
  const y = 22 + 6 * Math.cos(t / 6);
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(1100px 700px at ${x}% ${y}%, rgba(102,126,234,0.32), transparent 62%),
          radial-gradient(900px 640px at 86% 88%, rgba(118,75,162,0.30), transparent 62%),
          linear-gradient(160deg, #0b1726 0%, #12263b 55%, #1e4464 100%)`,
      }}
    />
  );
};

// ---------- Escena 1: gancho ----------
const Hook: React.FC = () => {
  const f = useCurrentFrame();
  const text = 'Hola, ¿tienen casas en Cholula?';
  const typed = Math.round(interpolate(f, [22, 46], [0, text.length], clamp));
  return (
    <Scene dur={D.hook}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', gap: 34, display: 'flex', flexDirection: 'column'}}>
        <Appear at={4}>
          <div style={{color: '#c9d6e6', fontSize: 34, fontWeight: 600, letterSpacing: 1, padding: '10px 26px', borderRadius: 999, background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.14)'}}>
            🌙 11:47 p. m.
          </div>
        </Appear>
        <Appear at={14}>
          <div style={{background: C.blue, color: C.white, fontSize: 44, fontWeight: 500, padding: '22px 34px', borderRadius: 30, borderBottomRightRadius: 8, boxShadow: '0 20px 50px rgba(0,0,0,0.35)', minWidth: 300}}>
            {text.slice(0, typed)}
            <span style={{opacity: f % 20 < 10 && typed < text.length ? 1 : 0}}>|</span>
          </div>
        </Appear>
        <Appear at={52} dist={36}>
          <div style={{color: C.white, fontSize: 92, fontWeight: 800, letterSpacing: -2, textAlign: 'center', lineHeight: 1.05}}>
            ¿Quién le contesta<br />a esta hora?
          </div>
        </Appear>
      </AbsoluteFill>
    </Scene>
  );
};

// ---------- Escena 2: presentación ----------
const Reveal: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f - 4, fps, config: {damping: 14, stiffness: 120}});
  return (
    <Scene dur={D.reveal}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', display: 'flex', flexDirection: 'column', gap: 22}}>
        <div style={{transform: `scale(${s})`, width: 150, height: 150, borderRadius: '50%', background: C.white, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 82, boxShadow: '0 24px 60px rgba(0,0,0,0.35)'}}>
          🏡
        </div>
        <Appear at={12}>
          <div style={{color: C.white, fontSize: 150, fontWeight: 800, letterSpacing: -4, lineHeight: 1}}>Sofía</div>
        </Appear>
        <Appear at={22}>
          <div style={{color: '#d5e1ef', fontSize: 46, fontWeight: 500}}>InmoBot · agente inmobiliario con tool use</div>
        </Appear>
        <Appear at={34}>
          <div style={{background: C.amberBg, color: C.amberInk, fontSize: 28, fontWeight: 700, padding: '10px 24px', borderRadius: 999}}>
            Demo técnica · catálogo ficticio
          </div>
        </Appear>
      </AbsoluteFill>
    </Scene>
  );
};

// ---------- Escena 3: el producto en uso ----------
const Bubble: React.FC<{who: 'user' | 'bot'; children: React.ReactNode}> = ({who, children}) => (
  <div style={{display: 'flex', justifyContent: who === 'user' ? 'flex-end' : 'flex-start', marginBottom: 14}}>
    <div
      style={{
        maxWidth: '84%', padding: '13px 17px', borderRadius: 20, fontSize: 20, lineHeight: 1.38,
        background: who === 'user' ? C.blue : C.white, color: who === 'user' ? C.white : '#333',
        boxShadow: who === 'user' ? 'none' : '0 2px 6px rgba(0,0,0,0.10)',
        borderBottomRightRadius: who === 'user' ? 6 : 20, borderBottomLeftRadius: who === 'bot' ? 6 : 20,
      }}
    >
      {children}
    </div>
  </div>
);

const Card: React.FC<{name: string; color: string; price: string; area: number}> = ({name, color, price, area}) => (
  <div style={{background: C.white, borderRadius: 14, overflow: 'hidden', marginBottom: 14, width: 372, boxShadow: '0 4px 12px rgba(0,0,0,0.12)'}}>
    <div style={{height: 118, background: color, color: C.white, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 700}}>
      {name}
    </div>
    <div style={{padding: '12px 16px'}}>
      <div style={{color: C.blue, fontWeight: 700, fontSize: 21, marginBottom: 4}}>{name}</div>
      <div style={{color: C.blueDark, fontWeight: 800, fontSize: 25, marginBottom: 4}}>{price} MXN</div>
      <div style={{color: C.gray, fontSize: 17}}>📍 Cholula · casa · 🛏️ 3 rec · 🚿 2 baños · 📏 {area} m²</div>
    </div>
  </div>
);

// Cada elemento nuevo crece desde altura 0 y empuja a los anteriores hacia arriba, como un chat real.
const ChatItem: React.FC<{at: number; h: number; children: React.ReactNode}> = ({at, h, children}) => {
  const f = useCurrentFrame();
  if (f < at) return null;
  const grow = interpolate(f, [at, at + 12], [0, h], {...clamp, easing: Easing.out(Easing.cubic)});
  const op = interpolate(f, [at + 3, at + 14], [0, 1], clamp);
  return <div style={{maxHeight: grow, opacity: op, overflow: 'hidden', flexShrink: 0}}>{children}</div>;
};

const Dots: React.FC<{from: number; to: number}> = ({from, to}) => {
  const f = useCurrentFrame();
  if (f < from || f >= to) return null;
  return (
    <div style={{display: 'flex', marginBottom: 14, flexShrink: 0}}>
      <div style={{background: C.white, borderRadius: 18, padding: '14px 18px', boxShadow: '0 2px 6px rgba(0,0,0,0.10)', display: 'flex', gap: 6}}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{width: 9, height: 9, borderRadius: 5, background: '#999', transform: `translateY(${-5 * Math.max(0, Math.sin((f - from) / 4 - i))}px)`}} />
        ))}
      </div>
    </div>
  );
};

const Caption: React.FC<{from: number; to: number; title: string; sub: string; n: number}> = ({from, to, title, sub, n}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [from, from + 14, to - 10, to], [0, 1, 1, 0], clamp);
  const y = interpolate(f, [from, from + 14], [26, 0], {...clamp, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{position: 'absolute', left: 0, top: 0, opacity: p, transform: `translateY(${y}px)`}}>
      <div style={{color: '#9fb6d3', fontSize: 30, fontWeight: 700, letterSpacing: 2, marginBottom: 14}}>{`0${n}`}</div>
      <div style={{color: C.white, fontSize: 74, fontWeight: 800, letterSpacing: -2, lineHeight: 1.05, marginBottom: 22}}>{title}</div>
      <div style={{color: '#d5e1ef', fontSize: 38, fontWeight: 500, lineHeight: 1.3, maxWidth: 820}}>{sub}</div>
    </div>
  );
};

const Product: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame: f, fps, config: {damping: 16, stiffness: 110}});
  const u1 = 'Busco casa en Cholula, hasta 2.5 millones, 3 recámaras';
  const typed = Math.round(interpolate(f, [18, 56], [0, u1.length], clamp));
  const inputText = f < 60 ? u1.slice(0, typed) : '';
  return (
    <Scene dur={D.product}>
      {/* Teléfono */}
      <div style={{position: 'absolute', left: 170, top: 36, transform: `translateY(${(1 - enter) * 60}px)`, opacity: enter}}>
        <div style={{width: 540, height: 930, borderRadius: 60, background: '#0a111c', padding: 14, boxShadow: '0 40px 90px rgba(0,0,0,0.5), inset 0 0 0 2px #26364a'}}>
          <div style={{width: '100%', height: '100%', borderRadius: 47, overflow: 'hidden', display: 'flex', flexDirection: 'column', background: C.light}}>
            <div style={{background: `linear-gradient(135deg, ${C.blue} 0%, ${C.blueDark} 100%)`, color: C.white, padding: '34px 22px 18px', display: 'flex', alignItems: 'center', gap: 14}}>
              <div style={{width: 46, height: 46, borderRadius: '50%', background: C.white, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24}}>🏡</div>
              <div>
                <div style={{fontWeight: 700, fontSize: 22}}>Sofía · InmoBot</div>
                <div style={{fontSize: 16, opacity: 0.9}}>Asesora virtual · demo con catálogo ficticio</div>
              </div>
            </div>
            <div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', padding: '16px 18px 4px', overflow: 'hidden', position: 'relative', WebkitMaskImage: 'linear-gradient(to bottom, transparent 0px, black 46px)'}}>
              <ChatItem at={0} h={150}><Bubble who="bot">👋 ¡Hola! Soy Sofía. ¿Qué tipo de propiedad buscas en Puebla? Puedes decirme zona, presupuesto y recámaras.</Bubble></ChatItem>
              <ChatItem at={60} h={110}><Bubble who="user">{u1}</Bubble></ChatItem>
              <Dots from={64} to={88} />
              <ChatItem at={88} h={170}>
                <Bubble who="bot">Encontré estas dos casas en Cholula que se ajustan a lo que buscas y las puedes ver en pantalla. ¿Tienes contemplado comprar de contado o mediante algún tipo de crédito?</Bubble>
              </ChatItem>
              <ChatItem at={100} h={260}><Card name="Casa Los Fresnos" color="#3a1a5c" price="$2,450,000" area={165} /></ChatItem>
              <ChatItem at={114} h={260}><Card name="Paseos de Cholula Residencial" color="#1a5c4a" price="$1,980,000" area={140} /></ChatItem>
              <ChatItem at={190} h={110}><Bubble who="user">Pagaría con crédito Infonavit y quiero mudarme en unos 2 meses</Bubble></ChatItem>
              <Dots from={196} to={214} />
              <ChatItem at={214} h={170}>
                <Bubble who="bot">Un asesor te puede confirmar la aceptación de tu crédito Infonavit para estas opciones. ¿Me podrías compartir tu nombre y un teléfono a 10 dígitos…?</Bubble>
              </ChatItem>
              <ChatItem at={262} h={110}><Bubble who="user">Me llamo Ana Prueba y mi teléfono es 222 123 4567</Bubble></ChatItem>
              <Dots from={268} to={284} />
              <ChatItem at={284} h={170}>
                <Bubble who="bot">Mucho gusto, Ana, ya guardé tus datos. ¿Te gustaría agendar una visita para conocer Casa Los Fresnos o Paseos de Cholula Residencial?</Bubble>
              </ChatItem>
              <ChatItem at={340} h={110}><Bubble who="user">Quiero visitar la Casa Los Fresnos el sábado en la mañana</Bubble></ChatItem>
              <Dots from={346} to={364} />
              <ChatItem at={364} h={170}>
                <Bubble who="bot">He registrado tu solicitud de visita para Casa Los Fresnos el sábado por la mañana. Un asesor humano te contactará para confirmar la fecha exacta…</Bubble>
              </ChatItem>
              <ChatItem at={380} h={120}>
                <div style={{background: C.greenBg, color: C.greenInk, borderRadius: 14, padding: '12px 16px', fontSize: 18, marginBottom: 14, maxWidth: 400, lineHeight: 1.35}}>
                  📅 Solicitud de visita registrada: Casa Los Fresnos · preferencia: sábado en la mañana. Un asesor la confirmará.
                </div>
              </ChatItem>
              <ChatItem at={398} h={80}>
                <div style={{display: 'inline-block', background: C.green, color: C.white, borderRadius: 999, padding: '13px 22px', fontWeight: 700, fontSize: 20, marginBottom: 12}}>
                  💬 Continuar por WhatsApp
                </div>
              </ChatItem>
            </div>
            <div style={{background: C.white, borderTop: '1px solid #e0e0e0', padding: 14, display: 'flex', gap: 10, alignItems: 'center'}}>
              <div style={{flex: 1, border: '1px solid #ccc', borderRadius: 26, padding: '13px 18px', fontSize: 18, color: inputText ? '#222' : '#999', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                {inputText || 'Escribe tu mensaje...'}
              </div>
              <div style={{width: 48, height: 48, borderRadius: '50%', background: C.blue, color: C.white, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20}}>➤</div>
            </div>
          </div>
        </div>
        <div style={{color: '#8fa6c2', fontSize: 18, marginTop: 14, width: 1000, whiteSpace: 'nowrap'}}>
          Recreación de la interfaz con mensajes y respuestas reales de Gemini (prueba del 14-oct, abreviadas).
        </div>
      </div>
      {/* Subtítulos */}
      <div style={{position: 'absolute', left: 860, top: 330, width: 900, height: 500}}>
        <Caption n={1} from={12} to={100} title="Califica al prospecto" sub="Zona, presupuesto, recámaras, forma de pago, plazo y contacto: una pregunta a la vez." />
        <Caption n={2} from={100} to={260} title="Muestra solo el catálogo" sub="Las tarjetas salen del resultado de la herramienta, no del texto del modelo." />
        <Caption n={3} from={260} to={340} title="Guarda el lead con puntaje" sub="Teléfono validado. Caliente, tibio o frío lo calcula el código, no el modelo." />
        <Caption n={4} from={340} to={D.product} title="Registra la visita y pasa a un humano" sub="Solicitud de visita confirmada por un asesor y botón de WhatsApp con el resumen." />
      </div>
    </Scene>
  );
};

// ---------- Escena 4: cómo funciona un turno ----------
const Box: React.FC<{at: number; title: string; sub: string; accent?: boolean}> = ({at, title, sub, accent}) => (
  <Appear at={at} dist={24} style={{width: 238}}>
    <div style={{height: 196, borderRadius: 22, padding: '22px 20px', background: accent ? `linear-gradient(135deg, ${C.blue}, ${C.blueDark})` : 'rgba(255,255,255,0.08)', border: accent ? '2px solid #7fa7d4' : '1px solid rgba(255,255,255,0.16)', boxShadow: '0 16px 40px rgba(0,0,0,0.25)'}}>
      <div style={{color: C.white, fontSize: 32, fontWeight: 800, marginBottom: 10}}>{title}</div>
      <div style={{color: '#cfdbea', fontSize: 22, lineHeight: 1.32}}>{sub}</div>
    </div>
  </Appear>
);

const Arrow: React.FC<{at: number}> = ({at}) => (
  <Appear at={at} dist={0} style={{width: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', height: 196}}>
    <div style={{color: '#9fb6d3', fontSize: 40, fontWeight: 700}}>→</div>
  </Appear>
);

const Badge: React.FC<{at: number; children: React.ReactNode}> = ({at, children}) => (
  <Appear at={at}>
    <div style={{background: 'rgba(255,255,255,0.10)', border: '1px solid rgba(255,255,255,0.18)', color: C.white, fontSize: 26, fontWeight: 600, padding: '15px 22px', borderRadius: 18, whiteSpace: 'nowrap'}}>
      {children}
    </div>
  </Appear>
);

const How: React.FC = () => (
  <Scene dur={D.how}>
    <AbsoluteFill style={{padding: '90px 96px', display: 'flex', flexDirection: 'column'}}>
      <Appear at={4}>
        <div style={{color: C.white, fontSize: 70, fontWeight: 800, letterSpacing: -2}}>Cómo funciona un turno</div>
      </Appear>
      <Appear at={12}>
        <div style={{color: '#cfdbea', fontSize: 36, marginTop: 10}}>El modelo decide qué herramienta usar; el código la ejecuta y la valida.</div>
      </Appear>
      <div style={{position: 'relative', marginTop: 170, display: 'flex', alignItems: 'center'}}>
        <Box at={24} title="Mensaje" sub="del prospecto" />
        <Arrow at={34} />
        <Box at={38} title="Guards" sub="1,000 caracteres · rate limit · presupuesto" />
        <Arrow at={48} />
        <Box at={52} title="Capa 1" sub="filtro determinista de injection" />
        <Arrow at={62} />
        <Box at={66} title="Agente" sub="límite duro de ~20 s por turno" accent />
        <Arrow at={76} />
        <Box at={80} title="Tools" sub="catálogo · leads · visitas · wa.me" />
        <Arrow at={90} />
        <Box at={94} title="Tarjetas" sub="solo desde resultados de tools" />
        <Appear at={104} dist={-20} style={{position: 'absolute', left: 3 * 282 + 4, top: -96, width: 238}}>
          <div style={{textAlign: 'center', background: C.white, color: C.blueDark, fontWeight: 800, fontSize: 24, borderRadius: 999, padding: '12px 0', whiteSpace: 'nowrap'}}>
            ⇅ Gemini · tool use
          </div>
        </Appear>
      </div>
      <div style={{display: 'flex', gap: 18, marginTop: 120}}>
        <Badge at={128}>⏱ Respuesta tardía: se descarta antes de ejecutar tools</Badge>
        <Badge at={142}>🛡 3 capas contra prompt injection</Badge>
        <Badge at={156}>🔒 Logs sin texto ni teléfonos</Badge>
      </div>
    </AbsoluteFill>
  </Scene>
);

// ---------- Escena 5: prueba ----------
const Tile: React.FC<{at: number; big: React.ReactNode; label: string; children?: React.ReactNode}> = ({at, big, label, children}) => (
  <Appear at={at} style={{flex: 1}}>
    <div style={{height: 360, borderRadius: 26, padding: '34px 30px', background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.16)', display: 'flex', flexDirection: 'column'}}>
      <div style={{color: C.white, fontSize: 92, fontWeight: 800, letterSpacing: -3, lineHeight: 1}}>{big}</div>
      <div style={{color: '#cfdbea', fontSize: 27, marginTop: 18, lineHeight: 1.3}}>{label}</div>
      <div style={{marginTop: 'auto'}}>{children}</div>
    </div>
  </Appear>
);

const Proof: React.FC = () => {
  const f = useCurrentFrame();
  const tests = Math.round(interpolate(f, [24, 60], [0, 88], {...clamp, easing: Easing.out(Easing.cubic)}));
  const runs = [true, false, false, false, true, true];
  return (
    <Scene dur={D.proof}>
      <AbsoluteFill style={{padding: '0 96px', display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <Appear at={4}>
          <div style={{color: C.white, fontSize: 70, fontWeight: 800, letterSpacing: -2}}>Probado contra el modelo real</div>
        </Appear>
        <Appear at={12}>
          <div style={{color: '#cfdbea', fontSize: 36, marginTop: 10}}>Cada falla tuvo diagnóstico, corrección y prueba de regresión.</div>
        </Appear>
        <div style={{display: 'flex', gap: 28, marginTop: 70}}>
          <Tile at={22} big={tests} label="pruebas en CI, sin red ni keys" />
          <Tile at={34} big="6" label="corridas contra Gemini real: 3 fallaron, 3 se corrigieron">
            <div style={{display: 'flex', gap: 12}}>
              {runs.map((ok, i) => {
                const p = interpolate(f, [70 + i * 9, 80 + i * 9], [0, 1], clamp);
                return (
                  <div key={i} style={{opacity: p, transform: `scale(${0.6 + 0.4 * p})`, width: 46, height: 46, borderRadius: '50%', background: ok ? C.green : C.red, color: C.white, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26, fontWeight: 800}}>
                    {ok ? '✓' : '✗'}
                  </div>
                );
              })}
            </div>
          </Tile>
          <Tile at={46} big="≈0.3" label="MXN por conversación de 5 turnos (medido)" />
          <Tile at={58} big={<span style={{fontSize: 80}}>3.0–5.7 s</span>} label="por turno en la corrida final" />
        </div>
        <Appear at={140}>
          <div style={{color: C.white, fontSize: 34, fontWeight: 600, marginTop: 50}}>
            Corrida final, sobre el código mergeado: <span style={{color: '#6fd39a'}}>3/3 escenarios críticos ✓</span> · 0 errores del proveedor
          </div>
        </Appear>
      </AbsoluteFill>
    </Scene>
  );
};

// ---------- Escena 6: cómo se construyó ----------
const Built: React.FC = () => {
  const f = useCurrentFrame();
  const steps = ['Spec', 'Plan', 'PR', 'CI', 'Prueba real', 'Verify', 'Revisión CTO', 'Deploy'];
  return (
    <Scene dur={D.built}>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', display: 'flex', flexDirection: 'column', gap: 46}}>
        <Appear at={4}>
          <div style={{color: C.white, fontSize: 78, fontWeight: 800, letterSpacing: -2}}>Construido con Claude Code</div>
        </Appear>
        <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
          {steps.map((s, i) => {
            const on = interpolate(f, [16 + i * 6, 24 + i * 6], [0, 1], clamp);
            return (
              <React.Fragment key={s}>
                <div style={{opacity: 0.25 + 0.75 * on, transform: `translateY(${(1 - on) * 14}px)`, background: on > 0.5 ? (i === steps.length - 1 ? C.green : C.blue) : 'rgba(255,255,255,0.08)', color: C.white, fontWeight: 700, fontSize: 30, padding: '16px 22px', borderRadius: 16, border: '1px solid rgba(255,255,255,0.2)'}}>
                  {s}
                </div>
                {i < steps.length - 1 && <div style={{color: '#9fb6d3', fontSize: 30, opacity: on}}>→</div>}
              </React.Fragment>
            );
          })}
        </div>
        <Appear at={66}>
          <div style={{color: '#d5e1ef', fontSize: 40, fontWeight: 500}}>Cada merge y cada deploy los aprueba una persona.</div>
        </Appear>
      </AbsoluteFill>
    </Scene>
  );
};

// ---------- Escena 7: cierre ----------
const Outro: React.FC = () => (
  <Scene dur={D.outro}>
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', display: 'flex', flexDirection: 'column', gap: 26}}>
      <Appear at={4}>
        <div style={{display: 'flex', alignItems: 'center', gap: 26}}>
          <div style={{width: 110, height: 110, borderRadius: '50%', background: C.white, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 60}}>🏡</div>
          <div style={{color: C.white, fontSize: 120, fontWeight: 800, letterSpacing: -3}}>Sofía · InmoBot</div>
        </div>
      </Appear>
      <Appear at={16}>
        <div style={{color: '#e6eef8', fontSize: 40, fontFamily: MONO, background: 'rgba(255,255,255,0.08)', padding: '14px 28px', borderRadius: 14}}>
          github.com/astraDukoWave/inmobot-demo
        </div>
      </Appear>
      <Appear at={28}>
        <div style={{color: '#cfdbea', fontSize: 36}}>Jonathan García · Puebla, México</div>
      </Appear>
    </AbsoluteFill>
  </Scene>
);

export const Main: React.FC = () => {
  let t = 0;
  const at = (d: number) => {
    const from = t;
    t += d;
    return from;
  };
  return (
    <AbsoluteFill style={{fontFamily: FONT}}>
      <Background />
      <Audio src={staticFile('music.wav')} volume={0.8} />
      <Sequence from={at(D.hook)} durationInFrames={D.hook}><Hook /></Sequence>
      <Sequence from={at(D.reveal)} durationInFrames={D.reveal}><Reveal /></Sequence>
      <Sequence from={at(D.product)} durationInFrames={D.product}><Product /></Sequence>
      <Sequence from={at(D.how)} durationInFrames={D.how}><How /></Sequence>
      <Sequence from={at(D.proof)} durationInFrames={D.proof}><Proof /></Sequence>
      <Sequence from={at(D.built)} durationInFrames={D.built}><Built /></Sequence>
      <Sequence from={at(D.outro)} durationInFrames={D.outro}><Outro /></Sequence>
    </AbsoluteFill>
  );
};
