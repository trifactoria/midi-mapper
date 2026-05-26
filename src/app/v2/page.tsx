import type { Metadata } from "next";
import { V2Shell } from "../../components/layout/V2Shell";

export const metadata: Metadata = {
  title: "V2 Shell",
};

export default function V2Page() {
  return <V2Shell />;
}

