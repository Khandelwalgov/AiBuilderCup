/** Approved raster artwork; color variants share the original proportions. */
export function BrandLogo() {
  return (
    <span className="brand-artwork">
      <img
        className="brand-full brand-full-dark"
        src="/brand/logo-dark.png"
        alt="Unclaimed"
        width="928"
        height="200"
      />
      <img
        className="brand-full brand-full-light"
        src="/brand/logo-light.png"
        alt="Unclaimed"
        width="928"
        height="200"
      />
      <img
        className="brand-symbol"
        src="/brand/icon.png"
        alt="Unclaimed"
        width="190"
        height="200"
      />
    </span>
  );
}
