import React from "react";
import { Img, delayRender, continueRender, useCurrentFrame } from "remotion";

export type StaticImageCardLayout = "standard" | "quote" | "meme";

export type StaticImageCardProps = {
  imageUrl: string;
  text: string;
  brandColor: string;
  fontFamily: string;
  platform: string;
  subtitle?: string;
  layout?: StaticImageCardLayout;
  // Meme-specific
  topText?: string;
  bottomText?: string;
};

// Platform-aware dimensions (used as fallback reference — Root.tsx sets the actual dimensions)
const PLATFORM_SIZES: Record<string, { width: number; height: number }> = {
  linkedin: { width: 1200, height: 1200 },
  instagram: { width: 1080, height: 1080 },
  x: { width: 1200, height: 675 },
};

export const StaticImageCard: React.FC<StaticImageCardProps> = ({
  imageUrl,
  text,
  brandColor,
  fontFamily,
  platform,
  subtitle,
  layout = "standard",
  topText,
  bottomText,
}) => {
  const frame = useCurrentFrame();
  const [handle] = React.useState(() => delayRender("Loading background image"));

  React.useEffect(() => {
    // continueRender is called after image loads via onLoad handler
    return () => {
      // cleanup
    };
  }, []);

  const platformSize = PLATFORM_SIZES[platform.toLowerCase()] || PLATFORM_SIZES.linkedin;

  const containerStyle: React.CSSProperties = {
    width: "100%",
    height: "100%",
    position: "relative",
    overflow: "hidden",
    fontFamily: fontFamily || "Inter, sans-serif",
    background: "#000",
  };

  const imageStyle: React.CSSProperties = {
    position: "absolute",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    objectFit: "cover",
  };

  // Standard layout: image background + brand color strip at bottom with text
  if (layout === "standard") {
    return (
      <div style={containerStyle}>
        {imageUrl && (
          <Img
            src={imageUrl}
            style={imageStyle}
            onLoad={() => continueRender(handle)}
            onError={() => continueRender(handle)}
          />
        )}
        {/* Semi-transparent overlay for readability */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            background: `linear-gradient(transparent, rgba(0,0,0,0.75))`,
            padding: "60px 48px 48px",
          }}
        >
          {/* Brand color accent line */}
          <div
            style={{
              height: 4,
              width: 60,
              background: brandColor,
              marginBottom: 16,
              borderRadius: 2,
            }}
          />
          <p
            style={{
              color: "#fff",
              fontSize: 36,
              fontWeight: 700,
              margin: 0,
              lineHeight: 1.3,
              textShadow: "0 2px 4px rgba(0,0,0,0.5)",
            }}
          >
            {text}
          </p>
          {subtitle && (
            <p
              style={{
                color: "rgba(255,255,255,0.8)",
                fontSize: 22,
                margin: "12px 0 0",
                fontWeight: 400,
              }}
            >
              {subtitle}
            </p>
          )}
        </div>
      </div>
    );
  }

  // Quote layout: large centered text with subtle branded background
  if (layout === "quote") {
    return (
      <div
        style={{
          ...containerStyle,
          background: "#0f172a",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "80px 60px",
        }}
      >
        {/* Decorative quote mark */}
        <div
          style={{
            fontSize: 120,
            color: brandColor,
            lineHeight: 1,
            marginBottom: 24,
            opacity: 0.6,
            fontFamily: "Georgia, serif",
          }}
        >
          "
        </div>
        <p
          style={{
            color: "#f8fafc",
            fontSize: 42,
            fontWeight: 600,
            textAlign: "center",
            lineHeight: 1.4,
            margin: 0,
            maxWidth: "85%",
          }}
        >
          {text}
        </p>
        {subtitle && (
          <div
            style={{
              marginTop: 40,
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <div
              style={{
                height: 2,
                width: 40,
                background: brandColor,
                borderRadius: 1,
              }}
            />
            <p
              style={{
                color: brandColor,
                fontSize: 20,
                margin: 0,
                fontWeight: 500,
                letterSpacing: "0.05em",
              }}
            >
              {subtitle}
            </p>
          </div>
        )}
      </div>
    );
  }

  // Meme layout: image background + top/bottom Impact-style text
  if (layout === "meme") {
    const memeTextStyle: React.CSSProperties = {
      color: "#fff",
      fontFamily: "Impact, 'Arial Black', Arial, sans-serif",
      fontSize: 56,
      fontWeight: 900,
      textAlign: "center",
      textTransform: "uppercase",
      textShadow:
        "-3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000",
      padding: "0 32px",
      lineHeight: 1.2,
      margin: 0,
    };

    return (
      <div style={containerStyle}>
        {imageUrl && (
          <Img
            src={imageUrl}
            style={imageStyle}
            onLoad={() => continueRender(handle)}
            onError={() => continueRender(handle)}
          />
        )}
        {/* Top text */}
        <div
          style={{
            position: "absolute",
            top: 24,
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
          }}
        >
          <p style={memeTextStyle}>{topText || text}</p>
        </div>
        {/* Bottom text */}
        {bottomText && (
          <div
            style={{
              position: "absolute",
              bottom: 24,
              left: 0,
              right: 0,
              display: "flex",
              justifyContent: "center",
            }}
          >
            <p style={memeTextStyle}>{bottomText}</p>
          </div>
        )}
      </div>
    );
  }

  // Default fallback — same as standard
  return <div style={containerStyle} />;
};
