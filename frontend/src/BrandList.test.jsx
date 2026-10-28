import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { beforeEach, describe, expect, it, vi } from "vitest";
import BrandList from "./BrandList.jsx";

const INDUSTRIES = [
  { slug: "insurance", name: "Insurance" },
  { slug: "telecom", name: "Telecom" },
];

const brand = (over = {}) => ({
  name: "Acme Insurance Co.",
  slug: "acme-insurance",
  industry: { name: "Insurance", slug: "insurance" },
  average_rating: 3.9,
  review_count: 12,
  short_description: "A long-running insurer.",
  top_review: {
    title: "Umbrella was easy",
    slug: "umbrella",
    rating: 5,
    snippet: "Painless.",
  },
  ...over,
});

const page = (results, count = results.length) => ({
  count,
  next: null,
  previous: null,
  results,
});
const ok = (body) =>
  Promise.resolve({ ok: true, json: () => Promise.resolve(body) });

function setup(fetchImpl, search = "") {
  window.history.replaceState(null, "", `/brands/${search}`);
  return render(<BrandList industries={INDUSTRIES} fetchImpl={fetchImpl} />);
}

beforeEach(() => window.history.replaceState(null, "", "/brands/"));

describe("BrandList", () => {
  it("renders a card per row with link, industry, rating, count, description and top review", async () => {
    setup(vi.fn(() => ok(page([brand()]))));
    const link = await screen.findByRole("link", {
      name: "Acme Insurance Co.",
    });
    expect(link).toHaveAttribute("href", "/brand/acme-insurance/");
    expect(
      screen.getByRole("img", { name: "Rated 3.9 out of 5" }),
    ).toBeInTheDocument();
    expect(screen.getByText("12 reviews")).toBeInTheDocument();
    expect(screen.getByText("A long-running insurer.")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Umbrella was easy" }),
    ).toHaveAttribute("href", "/review/umbrella/");
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });

  it("shows a busy status while loading", () => {
    setup(vi.fn(() => new Promise(() => {})));
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    expect(document.querySelector("[aria-busy='true']")).not.toBeNull();
  });

  it("filter and sort update the URL, reset to page 1 and request the API with page_size", async () => {
    const fetchImpl = vi.fn(() => ok(page([brand()], 20)));
    setup(fetchImpl, "?page=2");
    await screen.findByRole("link", { name: "Acme Insurance Co." });
    const user = userEvent.setup();
    await user.click(screen.getByRole("checkbox", { name: "Telecom" }));
    expect(window.location.search).toBe("?industry=telecom");
    await user.selectOptions(screen.getByLabelText("Sort by"), "-avg_rating");
    expect(window.location.search).toBe(
      "?industry=telecom&ordering=-avg_rating",
    );
    await waitFor(() => {
      const last = fetchImpl.mock.calls.at(-1)[0];
      expect(last).toContain("industry=telecom");
      expect(last).toContain("ordering=-avg_rating");
      expect(last).toContain("page=1");
      expect(last).toContain("page_size=6");
    });
  });

  it("filter and sort changes replace the history entry instead of adding one", async () => {
    setup(vi.fn(() => ok(page([brand()]))));
    await screen.findByRole("link", { name: "Acme Insurance Co." });
    const before = window.history.length;
    const user = userEvent.setup();
    await user.click(screen.getByRole("checkbox", { name: "Insurance" }));
    await user.click(screen.getByRole("checkbox", { name: "Telecom" }));
    await user.selectOptions(screen.getByLabelText("Sort by"), "-avg_rating");
    expect(window.location.search).toBe(
      "?industry=insurance&industry=telecom&ordering=-avg_rating",
    );
    expect(window.history.length).toBe(before);
  });

  it("keeps the previous results dimmed and busy while a new filter loads", async () => {
    let release;
    const fetchImpl = vi
      .fn()
      .mockImplementationOnce(() => ok(page([brand()])))
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            release = () =>
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve(
                    page([brand({ name: "Telco", slug: "telco" })]),
                  ),
              });
          }),
      );
    setup(fetchImpl);
    await screen.findByRole("link", { name: "Acme Insurance Co." });
    await userEvent
      .setup()
      .click(screen.getByRole("checkbox", { name: "Telecom" }));
    const section = document.querySelector("section.results");
    expect(section).toHaveAttribute("aria-busy", "true");
    expect(section).toHaveClass("is-fetching");
    expect(
      screen.getByRole("link", { name: "Acme Insurance Co." }),
    ).toBeInTheDocument();
    expect(document.querySelector(".skeleton-card")).toBeNull();
    act(() => release());
    await screen.findByRole("link", { name: "Telco" });
    expect(section).toHaveAttribute("aria-busy", "false");
  });

  it("shows skeleton cards on the first load only", () => {
    setup(vi.fn(() => new Promise(() => {})));
    expect(document.querySelectorAll(".skeleton-card")).toHaveLength(6);
  });

  it("shows an already-fetched URL immediately without a loading state", async () => {
    const fetchImpl = vi.fn(() => ok(page([brand()])));
    setup(fetchImpl);
    await screen.findByRole("link", { name: "Acme Insurance Co." });
    const user = userEvent.setup();
    const telecom = screen.getByRole("checkbox", { name: "Telecom" });
    await user.click(telecom);
    await waitFor(() =>
      expect(document.querySelector("section.results")).toHaveAttribute(
        "aria-busy",
        "false",
      ),
    );
    await user.click(telecom); // back to the unfiltered URL, fetched before
    const section = document.querySelector("section.results");
    expect(section).toHaveAttribute("aria-busy", "false");
    expect(section).not.toHaveClass("is-fetching");
  });

  it("restores controls from the URL and re-fetches on back/forward", async () => {
    const fetchImpl = vi.fn(() => ok(page([brand()])));
    setup(fetchImpl, "?industry=telecom&ordering=-review_count");
    await screen.findByRole("link", { name: "Acme Insurance Co." });
    expect(screen.getByRole("checkbox", { name: "Telecom" })).toBeChecked();
    expect(screen.getByLabelText("Sort by")).toHaveValue("-review_count");
    const calls = fetchImpl.mock.calls.length;
    act(() => {
      window.history.replaceState(null, "", "/brands/?industry=insurance");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await waitFor(() => expect(fetchImpl.mock.calls.length).toBe(calls + 1));
    expect(screen.getByRole("checkbox", { name: "Insurance" })).toBeChecked();
  });

  it("paginates with Next", async () => {
    const fetchImpl = vi.fn(() => ok(page([brand()], 13)));
    setup(fetchImpl);
    await screen.findByText("Page 1 of 3");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(window.location.search).toBe("?page=2");
    await screen.findByText("Page 2 of 3");
  });

  it("empty result offers Clear filters", async () => {
    const fetchImpl = vi.fn(() => ok(page([])));
    setup(fetchImpl, "?industry=telecom");
    await userEvent.click(
      await screen.findByRole("button", { name: "Clear filters" }),
    );
    expect(window.location.search).toBe("");
    expect(screen.getByRole("checkbox", { name: "Telecom" })).not.toBeChecked();
  });

  it("error shows Retry that refetches", async () => {
    const fetchImpl = vi
      .fn()
      .mockRejectedValueOnce(new Error("down"))
      .mockImplementation(() => ok(page([brand()])));
    setup(fetchImpl);
    await userEvent.click(await screen.findByRole("button", { name: "Retry" }));
    await screen.findByRole("link", { name: "Acme Insurance Co." });
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it("a page past the end falls back to page 1 instead of a dead error", async () => {
    const fetchImpl = vi.fn((url) =>
      url.includes("page=99")
        ? Promise.resolve({ ok: false, status: 404 })
        : ok(page([brand()])),
    );
    setup(fetchImpl, "?page=99");
    await screen.findByRole("link", { name: "Acme Insurance Co." });
    expect(window.location.search).toBe("");
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
  });

  it("ignores a stale response from a superseded request", async () => {
    let resolveFirst;
    const first = new Promise((res) => {
      resolveFirst = res;
    });
    const fetchImpl = vi
      .fn()
      .mockImplementationOnce(() => first)
      .mockImplementation(() =>
        ok(page([brand({ name: "Fresh Brand", slug: "fresh" })])),
      );
    setup(fetchImpl);
    await userEvent.click(screen.getByRole("checkbox", { name: "Telecom" }));
    await screen.findByRole("link", { name: "Fresh Brand" });
    await act(async () => {
      resolveFirst({
        ok: true,
        json: () => Promise.resolve(page([brand({ name: "Stale Brand" })])),
      });
    });
    expect(screen.queryByRole("link", { name: "Stale Brand" })).toBeNull();
    expect(
      screen.getByRole("link", { name: "Fresh Brand" }),
    ).toBeInTheDocument();
  });

  it("has an announced live region, fieldset legend and no serious axe violations", async () => {
    const { container } = setup(vi.fn(() => ok(page([brand()]))));
    await screen.findByRole("link", { name: "Acme Insurance Co." });
    expect(document.querySelector("[aria-live='polite']")).not.toBeNull();
    expect(screen.getByRole("group", { name: "Industry" })).toBeInTheDocument();
    const { violations } = await axe.run(container, {
      rules: { "color-contrast": { enabled: false } },
    });
    expect(
      violations.filter((v) => ["serious", "critical"].includes(v.impact)),
    ).toEqual([]);
  });
});
