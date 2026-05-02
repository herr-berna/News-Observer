const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";


async function request(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
}


export function fetchArticles() {
  return request("/articles");
}


export function fetchArticle(id) {
  return request(`/articles/${id}`);
}
