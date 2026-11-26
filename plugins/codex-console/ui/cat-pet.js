/**
 * Original MIT-licensed minimal pixel-art violet cat pet for Codex Console.
 * Clean-room 14x11 pixel grid rendered as crisp inline SVG + CSS keyframes.
 *
 * States:
 *  - 'working'   : briskly paces left <-> right across the runway with sparkle
 *  - 'strolling' : leisurely walks left <-> right for ~12 min after finishing work
 *  - 'sleeping'  : curls down with closed eyes & floating 'z Z z' after 12+ min idle
 *  - 'blocked'   : pauses alertly with a bouncing amber '!' indicator
 *  - 'meowing'   : triggered on click — stops, opens tiny mouth, pops '喵~' bubble
 */

export function renderPixelCat({
  mode = 'sleeping',
  label = '',
  meowing = false,
  freezeLeft = null,
  freezeFlip = 1,
}) {
  const effectiveMode = meowing
    ? 'meowing'
    : ['working', 'strolling', 'blocked', 'sleeping'].includes(mode)
      ? mode
      : 'sleeping';

  const eyesOpen = effectiveMode !== 'sleeping';
  const walkerStyle =
    meowing && typeof freezeLeft === 'number'
      ? `style="left:${freezeLeft.toFixed(1)}px"`
      : '';
  const svgStyle =
    meowing && (freezeFlip === -1 || freezeFlip === 1)
      ? `style="transform:scaleX(${freezeFlip})"`
      : '';

  const eyesSvg = eyesOpen
    ? `
      <rect x="4" y="4" width="1.2" height="2" fill="#18122b"/>
      <rect x="8.8" y="4" width="1.2" height="2" fill="#18122b"/>
    `
    : `
      <rect x="3.7" y="5" width="2.1" height="0.9" fill="#18122b"/>
      <rect x="8.2" y="5" width="2.1" height="0.9" fill="#18122b"/>
    `;

  const mouthSvg = meowing
    ? `<rect x="6.4" y="6.1" width="1.2" height="1.1" fill="#ec4899"/>`
    : '';

  let overlay = '';
  if (meowing) {
    overlay = `<span class="cat-meow" aria-hidden="true">喵~</span>`;
  } else if (effectiveMode === 'blocked') {
    overlay = `<span class="cat-badge blocked" aria-hidden="true">!</span>`;
  } else if (effectiveMode === 'working') {
    overlay = `<span class="cat-badge spark" aria-hidden="true">✦</span>`;
  } else if (effectiveMode === 'sleeping') {
    overlay = `<span class="cat-zzz" aria-hidden="true"><span>z</span><span>Z</span><span>z</span></span>`;
  }

  return `
    <button
      type="button"
      class="cat-runway mode-${effectiveMode} tip-trigger tip-bottom-right"
      id="btnCatPet"
      data-tip="${label}"
      aria-label="${label}"
    >
      <span class="cat-walker" ${walkerStyle}>
        ${overlay}
        <svg class="cat-svg" ${svgStyle} viewBox="0 0 14 11" width="23" height="18" shape-rendering="crispEdges" aria-hidden="true">
          <rect x="2" y="0" width="2" height="2" fill="#8b7be8"/>
          <rect x="10" y="0" width="2" height="2" fill="#8b7be8"/>
          <rect x="2" y="0" width="1" height="1" fill="#b4a7fa"/>
          <rect x="11" y="0" width="1" height="1" fill="#b4a7fa"/>
          <rect x="2" y="2" width="10" height="6" fill="#8b7be8"/>
          <rect x="1" y="3" width="1" height="4" fill="#7c6be0"/>
          <rect x="12" y="3" width="1" height="4" fill="#7c6be0"/>
          <rect x="3" y="2" width="8" height="1" fill="#a89bf7"/>
          <rect x="13" y="5" width="1" height="2" fill="#7c6be0"/>
          ${eyesSvg}
          ${mouthSvg}
          <g class="cat-legs-a">
            <rect x="3" y="8" width="1.5" height="2" fill="#7160d6"/>
            <rect x="5.5" y="8" width="1.5" height="2" fill="#7160d6"/>
            <rect x="8.5" y="8" width="1.5" height="2" fill="#7160d6"/>
            <rect x="10.5" y="8" width="1.5" height="2" fill="#7160d6"/>
          </g>
          <g class="cat-legs-b">
            <rect x="2.4" y="8" width="1.5" height="1.6" fill="#7160d6"/>
            <rect x="5.8" y="8" width="1.5" height="2.2" fill="#7160d6"/>
            <rect x="8.2" y="8" width="1.5" height="2.2" fill="#7160d6"/>
            <rect x="10.8" y="8" width="1.5" height="1.6" fill="#7160d6"/>
          </g>
        </svg>
      </span>
      <span class="cat-floor" aria-hidden="true"></span>
    </button>
  `;
}
