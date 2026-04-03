import React from "react";

export type DataPoint = {
  label: string;
  value: string;
  icon?: string;
};

export type InfographicProps = {
  title: string;
  dataPoints: DataPoint[];
  brandColor: string;
  style: string;
};

// Built-in SVG icon set
const ICONS: Record<string, React.FC<{ color: string; size: number }>> = {
  chart: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M4 20V10l5-5 4 4 5-7v18H4z"
        fill={color}
        opacity={0.9}
      />
    </svg>
  ),
  user: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="7" r="4" fill={color} />
      <path d="M2 21c0-5.523 4.477-10 10-10s10 4.477 10 10" fill={color} opacity={0.7} />
    </svg>
  ),
  clock: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke={color} strokeWidth="2" fill="none" />
      <path d="M12 7v5l3 3" stroke={color} strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  star: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  ),
  lightning: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
    </svg>
  ),
  target: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke={color} strokeWidth="2" />
      <circle cx="12" cy="12" r="5" stroke={color} strokeWidth="2" />
      <circle cx="12" cy="12" r="1" fill={color} />
    </svg>
  ),
};

function getIcon(
  iconName: string | undefined,
  color: string,
  size: number
): React.ReactNode {
  const key = (iconName || "chart").toLowerCase();
  const IconComponent = ICONS[key] || ICONS.chart;
  return <IconComponent color={color} size={size} />;
}

export const Infographic: React.FC<InfographicProps> = ({
  title,
  dataPoints,
  brandColor,
  style: _style,
}) => {
  const containerStyle: React.CSSProperties = {
    width: "100%",
    height: "100%",
    background: "#0f172a",
    display: "flex",
    flexDirection: "column",
    fontFamily: "Inter, sans-serif",
    padding: "60px 48px",
    boxSizing: "border-box",
  };

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={{ marginBottom: 48 }}>
        <div
          style={{
            height: 4,
            width: 60,
            background: brandColor,
            borderRadius: 2,
            marginBottom: 20,
          }}
        />
        <h1
          style={{
            color: "#f8fafc",
            fontSize: 48,
            fontWeight: 800,
            margin: 0,
            lineHeight: 1.2,
            letterSpacing: "-0.02em",
          }}
        >
          {title}
        </h1>
      </div>

      {/* Data points grid */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 24,
          flex: 1,
        }}
      >
        {dataPoints.map((point, index) => (
          <div
            key={index}
            style={{
              background: "rgba(255,255,255,0.05)",
              borderRadius: 16,
              padding: "28px 32px",
              display: "flex",
              alignItems: "center",
              gap: 28,
              border: `1px solid rgba(255,255,255,0.08)`,
              flex: 1,
            }}
          >
            {/* Icon */}
            <div
              style={{
                width: 64,
                height: 64,
                background: `${brandColor}22`,
                borderRadius: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              {getIcon(point.icon, brandColor, 32)}
            </div>

            {/* Content */}
            <div style={{ flex: 1 }}>
              <div
                style={{
                  color: brandColor,
                  fontSize: 40,
                  fontWeight: 800,
                  lineHeight: 1,
                  marginBottom: 8,
                  letterSpacing: "-0.02em",
                }}
              >
                {point.value}
              </div>
              <div
                style={{
                  color: "rgba(248,250,252,0.7)",
                  fontSize: 18,
                  fontWeight: 500,
                  lineHeight: 1.3,
                }}
              >
                {point.label}
              </div>
            </div>

            {/* Index indicator */}
            <div
              style={{
                color: "rgba(255,255,255,0.15)",
                fontSize: 64,
                fontWeight: 900,
                lineHeight: 1,
                letterSpacing: "-0.04em",
              }}
            >
              {String(index + 1).padStart(2, "0")}
            </div>
          </div>
        ))}
      </div>

      {/* Footer brand accent */}
      <div
        style={{
          marginTop: 36,
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
        <div
          style={{
            color: "rgba(255,255,255,0.3)",
            fontSize: 14,
            fontWeight: 500,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}
        >
          ThookAI
        </div>
      </div>
    </div>
  );
};
