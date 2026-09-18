import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("keeps native disabled semantics", () => {
    render(<Button disabled>Run query</Button>);

    expect(screen.getByRole("button", { name: "Run query" })).toBeDisabled();
  });
});
