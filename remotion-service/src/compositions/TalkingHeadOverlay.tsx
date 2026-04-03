import React from "react";
import {
  OffthreadVideo,
  useCurrentFrame,
  interpolate,
  useVideoConfig,
} from "remotion";

export type TalkingHeadOverlayProps = {
  videoUrl: string;
  overlayText: string;
  lowerThirdName: string;
  lowerThirdTitle: string;
  brandColor: string;
  durationInFrames?: number;
};

export const TalkingHeadOverlay: React.FC<TalkingHeadOverlayProps> = ({
  videoUrl,
  overlayText,
  lowerThirdName,
  lowerThirdTitle,
  brandColor,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Lower third animates in during first 30 frames (1 second), out in last 30
  const lowerThirdOpacity = interpolate(
    frame,
    [0, 30, durationInFrames - 30, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
  );

  const lowerThirdTranslateY = interpolate(
    frame,
    [0, 30],
    [30, 0],
    { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
  );

  // Overlay text fades in at frame 60 (2s), fades out 60 frames before end
  const overlayOpacity = interpolate(
    frame,
    [60, 90, durationInFrames - 60, durationInFrames - 30],
    [0, 1, 1, 0],
    { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
  );

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        overflow: "hidden",
        background: "#000",
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* HeyGen avatar video via OffthreadVideo for accurate frame extraction */}
      {videoUrl && (
        <OffthreadVideo
          src={videoUrl}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      )}

      {/* Overlay text banner — appears mid-video */}
      {overlayText && (
        <div
          style={{
            position: "absolute",
            top: "15%",
            left: "5%",
            right: "5%",
            opacity: overlayOpacity,
            background: "rgba(0,0,0,0.75)",
            borderLeft: `6px solid ${brandColor}`,
            padding: "16px 24px",
            borderRadius: "0 8px 8px 0",
          }}
        >
          <p
            style={{
              color: "#fff",
              fontSize: 28,
              fontWeight: 600,
              margin: 0,
              lineHeight: 1.4,
            }}
          >
            {overlayText}
          </p>
        </div>
      )}

      {/* Lower third name plate */}
      <div
        style={{
          position: "absolute",
          bottom: "12%",
          left: 0,
          opacity: lowerThirdOpacity,
          transform: `translateY(${lowerThirdTranslateY}px)`,
        }}
      >
        {/* Color accent bar */}
        <div
          style={{
            background: brandColor,
            padding: "6px 32px 6px 24px",
            marginBottom: 4,
            display: "inline-block",
          }}
        >
          <p
            style={{
              color: "#fff",
              fontSize: 28,
              fontWeight: 700,
              margin: 0,
              letterSpacing: "0.01em",
            }}
          >
            {lowerThirdName}
          </p>
        </div>
        {/* Title bar */}
        {lowerThirdTitle && (
          <div
            style={{
              background: "rgba(0,0,0,0.85)",
              padding: "6px 32px 6px 24px",
              display: "inline-block",
            }}
          >
            <p
              style={{
                color: "rgba(255,255,255,0.85)",
                fontSize: 20,
                fontWeight: 400,
                margin: 0,
                letterSpacing: "0.03em",
                textTransform: "uppercase",
              }}
            >
              {lowerThirdTitle}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
