import { useState } from "react";

import ArticleList from "./components/ArticleList";
import "./styles.css";


export default function App() {
  const [selectedArticle, setSelectedArticle] = useState(null);

  return (
    <main className="app">
      <section className="sidebar">
        <div className="header">
          <p>News Observer</p>
          <h1>Latest articles</h1>
        </div>
        <ArticleList
          onSelectArticle={setSelectedArticle}
          selectedArticle={selectedArticle}
        />
      </section>

      <section className="article-detail">
        {selectedArticle ? (
          <article>
            <p className="source">{selectedArticle.source}</p>
            <h2>{selectedArticle.title}</h2>
            <a href={selectedArticle.url} rel="noreferrer" target="_blank">
              Open original article
            </a>
            <div className="article-text">
              {selectedArticle.text || "No extracted text available."}
            </div>
          </article>
        ) : (
          <div className="empty-state">
            <h2>Select an article</h2>
            <p>Choose a story from the list to read the extracted text.</p>
          </div>
        )}
      </section>
    </main>
  );
}
