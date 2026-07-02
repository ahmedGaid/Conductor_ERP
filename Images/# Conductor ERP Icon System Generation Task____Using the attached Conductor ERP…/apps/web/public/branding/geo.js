// Conductor mark — single source of truth geometry.
// Math coords: origin = ring center, y-UP. Emits SCREEN-space path parts (y flipped).
(function (root) {
  const P = {
    Ro: 200, stroke: 50, theta: 60, capRound: true,
    barL: 174, barT: 42, gap: 28, X0: 26, shear: 0.60, radius: 9,
  };

  const sub = (a, b) => [a[0]-b[0], a[1]-b[1]];
  const add = (a, b) => [a[0]+b[0], a[1]+b[1]];
  const mul = (a, s) => [a[0]*s, a[1]*s];
  const len = (a) => Math.hypot(a[0], a[1]);
  const norm = (a) => { const l = len(a)||1; return [a[0]/l, a[1]/l]; };
  const shear = (p) => [p[0] + P.shear*p[1], p[1]];

  function barCorners() { // un-sheared rect corners per bar, math coords
    const half = P.barT/2, pitch = P.barT + P.gap;
    return [pitch, 0, -pitch].map(yc => {
      const x0 = P.X0, x1 = P.X0 + P.barL, yT = yc+half, yB = yc-half;
      return [[x0,yB],[x1,yB],[x1,yT],[x0,yT]].map(shear); // CCW
    });
  }

  function bbox() {
    let minx=-P.Ro, maxx=P.Ro, miny=-P.Ro, maxy=P.Ro;
    for (const poly of barCorners()) for (const p of poly) {
      minx=Math.min(minx,p[0]); maxx=Math.max(maxx,p[0]);
      miny=Math.min(miny,p[1]); maxy=Math.max(maxy,p[1]);
    }
    return { minx, miny, maxx, maxy, w:maxx-minx, h:maxy-miny };
  }

  function roundPoly(pts, r) {
    const n = pts.length; let d = '';
    for (let i=0;i<n;i++){
      const p0=pts[(i-1+n)%n], p1=pts[i], p2=pts[(i+1)%n];
      const v1=norm(sub(p0,p1)), v2=norm(sub(p2,p1));
      const rr=Math.min(r, len(sub(p0,p1))/2, len(sub(p2,p1))/2);
      const a=add(p1,mul(v1,rr)), b=add(p1,mul(v2,rr));
      d += (i===0?'M ':'L ') + fmt(a)+' Q '+fmt(p1)+' '+fmt(b)+' ';
    }
    return d + 'Z';
  }
  const fmt = (p) => p[0].toFixed(2)+' '+p[1].toFixed(2);

  // Build screen-space parts for a SxS viewBox with padding fraction.
  function parts(S, padFrac) {
    const bb = bbox();
    const avail = S*(1 - 2*padFrac);
    const scale = avail / Math.max(bb.w, bb.h);
    const cx=(bb.minx+bb.maxx)/2, cy=(bb.miny+bb.maxy)/2;
    const TX = (p) => [S/2 + (p[0]-cx)*scale, S/2 - (p[1]-cy)*scale]; // flip y

    // ring centerline arc, open on right between -theta..+theta
    const th = P.theta*Math.PI/180, R=(P.Ro - P.stroke/2);
    const a0=th, a1=2*Math.PI-th;
    const s=TX([R*Math.cos(a0), R*Math.sin(a0)]);
    const e=TX([R*Math.cos(a1), R*Math.sin(a1)]);
    const ringD = `M ${s[0].toFixed(2)} ${s[1].toFixed(2)} A ${(R*scale).toFixed(2)} ${(R*scale).toFixed(2)} 0 1 0 ${e[0].toFixed(2)} ${e[1].toFixed(2)}`;

    const bars = barCorners().map(poly => roundPoly(poly.map(TX), P.radius*scale));
    return {
      S, scale,
      ring: { d: ringD, width: P.stroke*scale, cap: P.capRound?'round':'butt' },
      bars,
    };
  }

  function svgMarkup(S, padFrac, fill) {
    const pr = parts(S, padFrac);
    let out = `<path d="${pr.ring.d}" fill="none" stroke="${fill}" stroke-width="${pr.ring.width.toFixed(3)}" stroke-linecap="${pr.ring.cap}"/>`;
    for (const d of pr.bars) out += `<path d="${d}" fill="${fill}"/>`;
    return out;
  }

  // ---- Squircle (superellipse) app-icon tile ----
  // Continuous-curvature rounded square, n≈5 ≈ Apple/iOS. Returns a closed cubic path.
  function squircleD(S, inset, n, samples) {
    n = n || 5; samples = samples || 28;
    const a = (S - 2 * inset) / 2, cx = S / 2, cy = S / 2;
    const pts = [];
    for (let i = 0; i < samples; i++) {
      const t = 2 * Math.PI * i / samples;
      const ct = Math.cos(t), st = Math.sin(t);
      const x = cx + a * Math.sign(ct) * Math.pow(Math.abs(ct), 2 / n);
      const y = cy + a * Math.sign(st) * Math.pow(Math.abs(st), 2 / n);
      pts.push([x, y]);
    }
    const N = pts.length;
    let d = `M ${pts[0][0].toFixed(2)} ${pts[0][1].toFixed(2)} `;
    for (let i = 0; i < N; i++) {
      const p0 = pts[(i - 1 + N) % N], p1 = pts[i], p2 = pts[(i + 1) % N], p3 = pts[(i + 2) % N];
      const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += `C ${c1[0].toFixed(2)} ${c1[1].toFixed(2)} ${c2[0].toFixed(2)} ${c2[1].toFixed(2)} ${p2[0].toFixed(2)} ${p2[1].toFixed(2)} `;
    }
    return d + 'Z';
  }

  // Full app-icon tile SVG markup: squircle bg + centered mark.
  // opts: { tileFill, markFill, markPad, inset }
  function tileMarkup(S, o) {
    const inset = o.inset || 0;
    const sq = squircleD(S, inset);
    let out = `<path d="${sq}" fill="${o.tileFill}"/>`;
    out += svgMarkup(S, o.markPad != null ? o.markPad : 0.24, o.markFill);
    return out;
  }

  root.ConductorGeo = { P, bbox, parts, svgMarkup, squircleD, tileMarkup };
})(typeof window !== 'undefined' ? window : globalThis);
