import type { Metadata } from "next";
import { V2Shell } from "../../components/layout/V2Shell";

export const metadata: Metadata = {
  title: "MIDI Mapper",
};

export default function V2Page() {
  return <V2Shell />;
}

