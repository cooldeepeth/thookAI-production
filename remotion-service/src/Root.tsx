import React from "react";
import { Composition } from "remotion";
import { StaticImageCard } from "./compositions/StaticImageCard";
import { ImageCarousel } from "./compositions/ImageCarousel";
import { Infographic } from "./compositions/Infographic";
import { TalkingHeadOverlay } from "./compositions/TalkingHeadOverlay";
import { ShortFormVideo } from "./compositions/ShortFormVideo";

export const Root: React.FC = () => {
  return (
    <>
      {/* Static image for social posts — supports standard, quote, and meme layouts */}
      <Composition
        id="StaticImageCard"
        component={StaticImageCard}
        width={1200}
        height={1200}
        fps={30}
        durationInFrames={1}
        defaultProps={{
          imageUrl: "",
          text: "",
          brandColor: "#2563EB",
          fontFamily: "Inter",
          platform: "linkedin",
          layout: "standard",
        }}
      />

      {/* Multi-slide carousel for LinkedIn / Instagram */}
      <Composition
        id="ImageCarousel"
        component={ImageCarousel}
        width={1080}
        height={1080}
        fps={30}
        durationInFrames={1}
        defaultProps={{
          slides: [],
          brandColor: "#2563EB",
          fontFamily: "Inter",
        }}
      />

      {/* Data-driven infographic with stats and icons */}
      <Composition
        id="Infographic"
        component={Infographic}
        width={1080}
        height={1350}
        fps={30}
        durationInFrames={1}
        defaultProps={{
          title: "",
          dataPoints: [],
          brandColor: "#2563EB",
          style: "clean",
        }}
      />

      {/* HeyGen avatar video with lower-third and text overlays */}
      <Composition
        id="TalkingHeadOverlay"
        component={TalkingHeadOverlay}
        width={1080}
        height={1920}
        fps={30}
        durationInFrames={900}
        defaultProps={{
          videoUrl: "",
          overlayText: "",
          lowerThirdName: "",
          lowerThirdTitle: "",
          brandColor: "#2563EB",
        }}
      />

      {/* Short-form video: multi-segment A-roll/B-roll with voice narration */}
      <Composition
        id="ShortFormVideo"
        component={ShortFormVideo}
        width={1080}
        height={1920}
        fps={30}
        durationInFrames={1800}
        defaultProps={{
          segments: [],
          audioUrl: "",
          musicUrl: "",
          brandColor: "#2563EB",
          durationInFrames: 1800,
        }}
      />
    </>
  );
};
