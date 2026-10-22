// Pi entry point for the dotbrain extension.
//
// Hands Pi the packaged skills beside this file. Pi honors each skill's own
// `disable-model-invocation` frontmatter, so explicit-only skills stay manual: hidden from the
// model, still available as `/skill:<name>`. Pi ranks these below the user's own skills, so a
// same-named skill of the user's wins and none loads twice.
//
// Pi runs this in its own process: Node built-ins only.

import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const VERSION = "0.12.0"; // x-release-please-version

const SKILLS = join(dirname(fileURLToPath(import.meta.url)), "skills");

export default function (pi) {
  pi.on("resources_discover", () => ({ skillPaths: [SKILLS] }));
}
