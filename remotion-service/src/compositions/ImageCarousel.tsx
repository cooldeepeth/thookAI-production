import React from "react";
import { Series, Img, delayRender, continueRender } from "remotion";

export type CarouselSlide = {
  imageUrl: string;
  text: string;
  slideNumber: number;
};

export type ImageCarouselProps = {
  slides: CarouselSlide[];
  brandColor: string;
  fontFamily: string;
};

const MAX_SLIDES = 10;
const FRAMES_PER_SLIDE = 90; // 3 seconds at 30fps

const SlideItem: React.FC<{
  slide: CarouselSlide;
  totalSlides: number;
  brandColor: string;
  fontFamily: string;
}> = ({ slide, totalSlides, brandColor, fontFamily }) => {
  const [handle] = React.useState(() =>
    delayRender(`Loading slide ${slide.slideNumber} image`)
  );

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        overflow: "hidden",
        fontFamily: fontFamily || "Inter, sans-serif",
        background: "#1e293b",
      }}
    >
      {slide.imageUrl && (
        <Img
          src={slide.imageUrl}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
          onLoad={() => continueRender(handle)}
          onError={() => continueRender(handle)}
        />
      )}

      {/* Gradient overlay */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          background:
            "linear-gradient(transparent 20%, rgba(0,0,0,0.8) 100%)",
          padding: "80px 40px 100px",
        }}
      >
        <p
          style={{
            color: "#fff",
            fontSize: 34,
            fontWeight: 600,
            margin: 0,
            lineHeight: 1.4,
            textShadow: "0 2px 4px rgba(0,0,0,0.5)",
          }}
        >
          {slide.text}
        </p>
      </div>

      {/* Dot pagination */}
      <div
        style={{
          position: "absolute",
          bottom: 28,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: 8,
        }}
      >
        {Array.from({ length: totalSlides }).map((_, i) => (
          <div
            key={i}
            style={{
              width: i === slide.slideNumber - 1 ? 24 : 8,
              height: 8,
              borderRadius: 4,
              background:
                i === slide.slideNumber - 1 ? brandColor : "rgba(255,255,255,0.4)",
              transition: "all 0.3s ease",
            }}
          />
        ))}
      </div>

      {/* Slide number badge */}
      <div
        style={{
          position: "absolute",
          top: 24,
          right: 24,
          background: brandColor,
          color: "#fff",
          width: 48,
          height: 48,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 18,
          fontWeight: 700,
        }}
      >
        {slide.slideNumber}
      </div>
    </div>
  );
};

export const ImageCarousel: React.FC<ImageCarouselProps> = ({
  slides,
  brandColor,
  fontFamily,
}) => {
  // Enforce max 10 slides
  const cappedSlides = slides.slice(0, MAX_SLIDES);

  if (cappedSlides.length === 0) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#1e293b",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <p style={{ color: "#fff", fontSize: 24 }}>No slides provided</p>
      </div>
    );
  }

  return (
    <Series>
      {cappedSlides.map((slide) => (
        <Series.Sequence key={slide.slideNumber} durationInFrames={FRAMES_PER_SLIDE}>
          <SlideItem
            slide={slide}
            totalSlides={cappedSlides.length}
            brandColor={brandColor}
            fontFamily={fontFamily}
          />
        </Series.Sequence>
      ))}
    </Series>
  );
};
