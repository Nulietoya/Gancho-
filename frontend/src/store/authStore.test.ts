import { afterEach, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { useAuthStore } from "./authStore";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  useAuthStore.setState({
    accessToken: null,
    refreshToken: null,
    user: null,
    status: "idle",
    error: null,
  });
});

it("renova o token uma vez para chamadas simultâneas", async () => {
  let complete!: (tokens: { access_token: string; refresh_token: string }) => void;
  const request = new Promise<{ access_token: string; refresh_token: string }>((resolve) => {
    complete = resolve;
  });
  const rawJson = vi.spyOn(client, "rawJson").mockReturnValue(request);
  useAuthStore.setState({ refreshToken: "old" });

  const first = useAuthStore.getState().refresh();
  const second = useAuthStore.getState().refresh();
  expect(rawJson).toHaveBeenCalledTimes(1);

  complete({ access_token: "new-access", refresh_token: "new-refresh" });
  expect(await Promise.all([first, second])).toEqual(["new-access", "new-access"]);
  expect(useAuthStore.getState().refreshToken).toBe("new-refresh");
  expect(localStorage.getItem("gancho_refresh_token")).toBe("new-refresh");
});

