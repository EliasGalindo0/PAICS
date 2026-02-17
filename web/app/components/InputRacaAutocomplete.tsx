"use client";

import { useState, useRef, useEffect } from "react";
import { filtrarRacas } from "@/lib/racas";

interface InputRacaAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  especie?: string;
  name?: string;
  id?: string;
  placeholder?: string;
  style?: React.CSSProperties;
  disabled?: boolean;
}

export function InputRacaAutocomplete({
  value,
  onChange,
  especie,
  name,
  id,
  placeholder,
  style,
  disabled,
}: InputRacaAutocompleteProps) {
  const [focused, setFocused] = useState(false);
  const [showList, setShowList] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const sugestoes = filtrarRacas(value, especie);
  const selecaoExata =
    sugestoes.length === 1 && sugestoes[0].toLowerCase() === value.trim().toLowerCase();
  const deveMostrarLista =
    focused && value.trim().length > 0 && sugestoes.length > 0 && !selecaoExata;

  useEffect(() => {
    setShowList(deveMostrarLista);
  }, [deveMostrarLista]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setFocused(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} style={{ position: "relative", width: "100%" }}>
      <input
        type="text"
        name={name}
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setTimeout(() => setFocused(false), 150)}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        style={{
          width: "100%",
          padding: 8,
          borderRadius: 6,
          border: "1px solid var(--border-input, #d1d5db)",
          background: "var(--bg-input, #fff)",
          color: "var(--text, #1e293b)",
          boxSizing: "border-box",
          ...style,
        }}
      />
      {showList && (
        <ul
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            margin: 0,
            padding: 0,
            listStyle: "none",
            background: "var(--bg-card, #fff)",
            border: "1px solid var(--border-input, #d1d5db)",
            borderRadius: 6,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            maxHeight: 200,
            overflowY: "auto",
            zIndex: 100,
            marginTop: 4,
          }}
        >
          {sugestoes.map((raca) => (
            <li
              key={raca}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(raca);
                setShowList(false);
              }}
              style={{
                padding: "10px 12px",
                cursor: "pointer",
                fontSize: "0.95rem",
                borderBottom: "1px solid var(--bg-muted, #f3f4f6)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--bg-thead, #f3f4f6)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
              }}
            >
              {raca}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
