import React from "react";
import {
  Series,
  Audio,
  OffthreadVideo,
  Img,
  useCurrentFrame,
  spring,
  useVideoConfig,
  interpolate,
  delayRender,
  continueRender,
} from "remotion";

export type VideoSegment = {
  type: "video" | "image";
  url: string;
  durationInFrames: number;
  text?: string;
};

export type ShortFormVideoProps = {
  segments: VideoSegment[];
  audioUrl?: string;
  musicUrl?: string;
  brandColor: string;
  durationInFrames: number;
};

const SegmentOverlay: React.FC<{
  segment: VideoSegment;
  brandColor: string;
}> = ({ segment, brandColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Spring animation for text entrance
  const textProgress = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 200, mass: 0.8 },
  });

  const textTranslateY = interpolate(textProgress, [0, 1], [40, 0]);
  const textOpacity = textProgress;

  const [imgHandle] = React.useState(() =>
    segment.type === "image" ? delayRender("Loading segment image") : null
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
      {/* Media layer */}
      {segment.type === "video" ? (
        <OffthreadVideo
          src={segment.url}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      ) : (
        <Img
          src={segment.url}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
          onLoad={() => imgHandle && continueRender(imgHandle)}
          onError={() => imgHandle && continueRender(imgHandle)}
        />
      )}

      {/* Gradient overlay for text readability */}
      {segment.text && (
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            background:
              "linear-gradient(transparent, rgba(0,0,0,0.8) 40%, rgba(0,0,0,0.9) 100%)",
            padding: "100px 40px 80px",
          }}
        >
          {/* Brand accent line */}
          <div
            style={{
              height: 3,
              width: 50,
              background: brandColor,
              borderRadius: 2,
              marginBottom: 16,
              opacity: textOpacity,
            }}
          />
          <p
            style={{
              color: "#fff",
              fontSize: 36,
              fontWeight: 700,
              margin: 0,
              lineHeight: 1.35,
              transform: `translateY(${textTranslateY}px)`,
              opacity: textOpacity,
              textShadow: "0 2px 8px rgba(0,0,0,0.6)",
            }}
          >
            {segment.text}
          </p>
        </div>
      )}
    </div>
  );
};

export const ShortFormVideo: React.FC<ShortFormVideoProps> = ({
  segments,
  audioUrl,
  musicUrl,
  brandColor,
}) => {
  if (segments.length === 0) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#0f172a",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <p style={{ color: "#fff", fontSize: 24 }}>No segments provided</p>
      </div>
    );
  }

  return (
    <>
      {/* Video segments via Series */}
      <Series>
        {segments.map((segment, index) => (
          <Series.Sequence key={index} durationInFrames={segment.durationInFrames}>
            <SegmentOverlay segment={segment} brandColor={brandColor} />
          </Series.Sequence>
        ))}
      </Series>

      {/* Voice narration audio track */}
      {audioUrl && (
        <Audio src={audioUrl} volume={1.0} />
      )}

      {/* Background music at lower volume */}
      {musicUrl && (
        <Audio src={musicUrl} volume={0.15} />
      )}
    </>
  );
};
