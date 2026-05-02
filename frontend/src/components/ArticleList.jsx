import { useEffect, useState } from "react";

import { fetchArticles } from "../api";
import ArticleCard from "./ArticleCard";


export default function ArticleList({ selectedArticle, onSelectArticle }) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchArticles()
      .then(setArticles)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="status">Loading articles...</p>;
  }

  if (error) {
    return <p className="status error">Could not load articles: {error}</p>;
  }

  if (articles.length === 0) {
    return <p className="status">No articles collected yet.</p>;
  }

  return (
    <div className="article-list">
      {articles.map((article) => (
        <ArticleCard
          article={article}
          key={article.id}
          onSelect={onSelectArticle}
          selected={selectedArticle?.id === article.id}
        />
      ))}
    </div>
  );
}
