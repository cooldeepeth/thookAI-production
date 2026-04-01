import {
  S3Client,
  PutObjectCommand,
  PutObjectCommandInput,
} from "@aws-sdk/client-s3";
import * as fs from "fs";
import * as path from "path";

const R2_ENDPOINT = process.env.R2_ENDPOINT;
const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID;
const R2_SECRET_ACCESS_KEY = process.env.R2_SECRET_ACCESS_KEY;
const R2_BUCKET_NAME = process.env.R2_BUCKET_NAME;
const R2_PUBLIC_URL = process.env.R2_PUBLIC_URL;

function isR2Configured(): boolean {
  return !!(
    R2_ENDPOINT &&
    R2_ACCESS_KEY_ID &&
    R2_SECRET_ACCESS_KEY &&
    R2_BUCKET_NAME &&
    R2_PUBLIC_URL
  );
}

function createS3Client(): S3Client {
  return new S3Client({
    endpoint: R2_ENDPOINT,
    region: "auto",
    credentials: {
      accessKeyId: R2_ACCESS_KEY_ID as string,
      secretAccessKey: R2_SECRET_ACCESS_KEY as string,
    },
    forcePathStyle: false,
  });
}

export async function uploadToR2(
  buffer: Buffer,
  key: string,
  contentType: string
): Promise<string> {
  if (!isR2Configured()) {
    console.warn(
      "[R2Upload] R2 env vars not configured — falling back to local /tmp storage"
    );
    const localPath = path.join("/tmp", key.replace(/\//g, "_"));
    fs.mkdirSync(path.dirname(localPath), { recursive: true });
    fs.writeFileSync(localPath, buffer);
    return localPath;
  }

  const client = createS3Client();

  const params: PutObjectCommandInput = {
    Bucket: R2_BUCKET_NAME as string,
    Key: key,
    Body: buffer,
    ContentType: contentType,
  };

  await client.send(new PutObjectCommand(params));

  return `${R2_PUBLIC_URL}/${key}`;
}
