import { createBrowserRouter } from "react-router";
import { Home } from "./pages/Home";
import { SearchResults } from "./pages/SearchResults";
import { About } from "./pages/About";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Home,
  },
  {
    path: "/search",
    Component: SearchResults,
  },
  {
    path: "/about",
    Component: About,
  },
]);
