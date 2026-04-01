import express, { Request, Response } from "express";
import path from "path";
import os from "os";
import fs from "fs";
import { bundle } from "@remotion/bundler";
import {
  selectComposition,
  renderMedia,
  renderStill,
} from "@remotion/renderer";
import { createJob, getJob, updateJob } from "./lib/job-store";
import { uploadToR2 } from "./lib/r2-upload";

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;

// Bundle caching — called once at startup, reused for all renders
let bundlePath: string | null = null;

async function getBundlePath(): Promise<string> {
  if (bundlePath) {
    return bundlePath;
  }
  console.log("[Remotion] Bundling compositions — this takes ~30s on first run");
  const entryPoint = path.resolve(__dirname, "./src/index.ts");
  bundlePath = await bundle({
    entryPoint,
    webpackOverride: (config) => config,
  });
  console.log(`[Remotion] Bundle ready at: ${bundlePath}`);
  return bundlePath;
}

// Determine render type from composition ID if not specified
function inferRenderType(
  compositionId: string,
  override?: string
): "still" | "video" {
  if (override === "still" || override === "video") {
    return override;
  }
  const stillCompositions = ["StaticImageCard", "Infographic"];
  return stillCompositions.includes(compositionId) ? "still" : "video";
}

// Get file extension for output
function getOutputExtension(renderType: "still" | "video"): string {
  return renderType === "still" ? "png" : "mp4";
}

// Background render function — updates job store and uploads to R2
async function runRender(
  renderId: string,
  compositionId: string,
  inputProps: Record<string, unknown>,
  renderType: "still" | "video"
): Promise<void> {
  try {
    updateJob(renderId, { status: "rendering" });

    const serveUrl = await getBundlePath();

    const composition = await selectComposition({
      serveUrl,
      id: compositionId,
      inputProps,
    });

    const ext = getOutputExtension(renderType);
    const tmpPath = path.join(os.tmpdir(), `remotion-${renderId}.${ext}`);

    if (renderType === "still") {
      await renderStill({
        composition,
        serveUrl,
        output: tmpPath,
        inputProps,
        imageFormat: "png",
      });
    } else {
      await renderMedia({
        composition,
        serveUrl,
        codec: "h264",
        outputLocation: tmpPath,
        inputProps,
        timeoutInMilliseconds: 120000,
        ...(process.env.REMOTION_LICENSE_KEY
          ? { logLevel: "info" }
          : {}),
      });
    }

    const buffer = fs.readFileSync(tmpPath);
    const contentType = renderType === "still" ? "image/png" : "video/mp4";
    const r2Key = `media/renders/${renderId}.${ext}`;

    const url = await uploadToR2(buffer, r2Key, contentType);

    // Clean up tmp file
    try {
      fs.unlinkSync(tmpPath);
    } catch {
      // Non-critical cleanup failure
    }

    updateJob(renderId, { status: "done", url });
    console.log(`[Remotion] Render ${renderId} complete: ${url}`);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.error(`[Remotion] Render ${renderId} failed: ${message}`);
    updateJob(renderId, { status: "failed", error: message });
  }
}

// POST /render — accept render request, return render_id immediately
app.post("/render", (req: Request, res: Response) => {
  const {
    composition_id,
    input_props = {},
    render_type,
  } = req.body as {
    composition_id?: string;
    input_props?: Record<string, unknown>;
    render_type?: string;
  };

  if (!composition_id) {
    res.status(400).json({ error: "composition_id is required" });
    return;
  }

  const resolvedRenderType = inferRenderType(composition_id, render_type);
  const renderId = createJob(composition_id);

  // Fire and forget — do not await
  runRender(renderId, composition_id, input_props, resolvedRenderType).catch(
    (err: unknown) => {
      console.error(`[Remotion] Unhandled error in runRender: ${err}`);
    }
  );

  res.status(200).json({ render_id: renderId });
});

// GET /render/:id/status — return current job status
app.get("/render/:id/status", (req: Request, res: Response) => {
  const job = getJob(req.params.id);
  if (!job) {
    res.status(404).json({ error: "not_found" });
    return;
  }
  res.json(job);
});

// GET /health — liveness check
app.get("/health", (_req: Request, res: Response) => {
  res.json({
    status: "ok",
    bundled: !!bundlePath,
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`[Remotion] Service starting on port ${PORT}`);

  // Pre-warm bundle on startup (non-blocking)
  getBundlePath().catch((err: unknown) => {
    console.error(`[Remotion] Pre-warm bundle failed: ${err}`);
  });
});

export default app;
