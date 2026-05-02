PART1 = r"""% ============================================================================
% ChatHCE - Arquitectura Tecnica Detallada del Sistema
% Documento de Arquitectura v2.1.0 - Abril 2026
% ============================================================================
\documentclass[11pt,a4paper]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish]{babel}
\usepackage{lmodern}
\usepackage[margin=2.5cm,top=3cm,bottom=3cm]{geometry}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{multirow}
\usepackage{enumitem}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{float}
\usepackage{amsmath}
\usepackage{listings}
\usepackage{tcolorbox}
\usepackage{setspace}
\usepackage{longtable}
\usepackage{array}
\usepackage{colortbl}
\usepackage{rotating}
\usepackage{pdflscape}
\usepackage{makecell}
\usepackage{pifont}

\usepackage{tikz}
\usetikzlibrary{
  shapes.geometric,
  shapes.multipart,
  arrows.meta,
  positioning,
  fit,
  backgrounds,
  calc,
  decorations.pathreplacing,
  matrix,
  shadows.blur,
  patterns
}

% --- Colores ---
\definecolor{primary}{HTML}{1A5276}
\definecolor{secondary}{HTML}{2E86C1}
\definecolor{accent}{HTML}{E74C3C}
\definecolor{success}{HTML}{27AE60}
\definecolor{warning}{HTML}{F39C12}
\definecolor{lightbg}{HTML}{EBF5FB}
\definecolor{darkbg}{HTML}{1B2631}
\definecolor{codebg}{HTML}{F4F6F7}
\definecolor{ragcolor}{HTML}{8E44AD}
\definecolor{dbcolor}{HTML}{2980B9}
\definecolor{vizcolor}{HTML}{E67E22}
\definecolor{seccolor}{HTML}{C0392B}
\definecolor{layerbg1}{HTML}{D6EAF8}
\definecolor{layerbg2}{HTML}{D5F5E3}
\definecolor{layerbg3}{HTML}{FDEBD0}
\definecolor{layerbg4}{HTML}{FADBD8}
\definecolor{layerbg5}{HTML}{E8DAEF}
\definecolor{graylight}{HTML}{F2F3F4}
\definecolor{graymid}{HTML}{BDC3C7}
\definecolor{cachecolor}{HTML}{1ABC9C}
\definecolor{perfcolor}{HTML}{F39C12}

% --- Estilos TikZ ---
\tikzset{
  base/.style={draw, rounded corners=3pt, minimum height=0.8cm,
    font=\footnotesize\sffamily, align=center, text=white},
  component/.style={base, fill=secondary, minimum width=2.5cm},
  tool/.style={base, fill=success, minimum width=2cm},
  layer/.style={draw=gray!50, rounded corners=5pt, inner sep=8pt,
    font=\footnotesize\sffamily},
  arrow/.style={-{Stealth[length=5pt]}, thick, color=primary},
  dashedarrow/.style={-{Stealth[length=5pt]}, dashed, thick, color=gray!60},
  biarrow/.style={{Stealth[length=5pt]}-{Stealth[length=5pt]}, thick, color=primary},
  label/.style={font=\tiny\sffamily\itshape, text=gray!70},
  process/.style={draw=primary, fill=primary!10, rounded corners=3pt,
    minimum width=3.5cm, minimum height=0.65cm,
    font=\small\sffamily, align=center, text=primary},
  decision/.style={draw=warning!80!black, fill=warning!15, diamond, aspect=2.8,
    font=\small\sffamily, align=center, text=warning!80!black, inner sep=1pt},
  io/.style={draw=success!70, fill=success!10, rounded corners=3pt,
    minimum width=3cm, minimum height=0.55cm,
    font=\small\sffamily, align=center, text=success!80!black},
  dbbox/.style={draw=dbcolor!70, fill=dbcolor!10, rounded corners=3pt,
    minimum width=3cm, minimum height=0.6cm,
    font=\small\sffamily, align=center, text=dbcolor!80},
  ragbox/.style={draw=ragcolor!70, fill=ragcolor!10, rounded corners=3pt,
    minimum width=3cm, minimum height=0.6cm,
    font=\small\sffamily, align=center, text=ragcolor!80},
  vizbox/.style={draw=vizcolor!70, fill=vizcolor!10, rounded corners=3pt,
    minimum width=3cm, minimum height=0.6cm,
    font=\small\sffamily, align=center, text=vizcolor!80},
  modelbox/.style={draw=accent!60, fill=accent!8, rounded corners=3pt,
    minimum width=3cm, minimum height=0.55cm,
    font=\small\sffamily\bfseries, text=accent!80, align=center},
  servicebox/.style={draw=gray!50, fill=gray!8, rounded corners=3pt,
    minimum width=2.8cm, minimum height=0.55cm,
    font=\small\sffamily, align=center},
  tblbox/.style={draw=#1!70, fill=#1!18, rounded corners=2pt,
    minimum width=2.6cm, minimum height=0.5cm,
    font=\footnotesize\sffamily\bfseries, text=#1!80, align=center},
  layerbox/.style={draw=#1!60, fill=#1!6, rounded corners=5pt,
    inner sep=10pt, font=\small\sffamily}
}

% --- listings ---
\lstset{
  basicstyle=\ttfamily\small,
  backgroundcolor=\color{codebg},
  frame=single, rulecolor=\color{gray!30},
  breaklines=true, columns=fullflexible,
  keepspaces=true, showstringspaces=false,
  commentstyle=\color{success},
  keywordstyle=\color{primary}\bfseries,
  stringstyle=\color{accent}
}

\tcbuselibrary{skins,breakable}

% --- Encabezados ---
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\footnotesize\textcolor{primary}{\textbf{ChatHCE}} -- Arquitectura T\'ecnica Detallada}
\fancyhead[R]{\footnotesize\textcolor{gray}{v2.1.0 | Abril 2026}}
\fancyfoot[C]{\footnotesize\thepage}
\renewcommand{\headrulewidth}{0.4pt}

% --- Secciones ---
\titleformat{\section}{\Large\bfseries\color{primary}}{\thesection.}{0.5em}{}[{\color{primary}\titlerule[0.5pt]}]
\titleformat{\subsection}{\large\bfseries\color{secondary}}{\thesubsection}{0.5em}{}
\titleformat{\subsubsection}{\normalsize\bfseries\color{gray!80}}{\thesubsubsection}{0.5em}{}
\titlespacing*{\section}{0pt}{1.5em}{0.8em}
\titlespacing*{\subsection}{0pt}{1em}{0.5em}
\titlespacing*{\subsubsection}{0pt}{0.7em}{0.3em}

\setlength{\parskip}{0.4em}
\setlength{\parindent}{0em}

\hypersetup{colorlinks=true, linkcolor=primary, citecolor=primary, urlcolor=secondary,
  pdftitle={ChatHCE Arquitectura Tecnica}, pdfauthor={ChatHCE Team}}

% ============================================================================
\begin{document}
% ============================================================================

\begin{titlepage}
\centering
\vspace*{2cm}
{\Huge\bfseries\textcolor{primary}{ChatHCE}\\[0.5em]}
{\LARGE\bfseries\textcolor{secondary}{Arquitectura T\'ecnica Detallada\\[0.3em]del Sistema de An\'alisis Cl\'inico Inteligente}\\[1.5em]}
{\large Documento de Arquitectura del Sistema\\[0.3em]}
{\normalsize\textcolor{gray}{Versi\'on 2.1.0 \quad$\bullet$\quad Abril 2026}\\[2em]}
\textcolor{primary}{\rule{0.7\textwidth}{1pt}}\\[2em]
\begin{tcolorbox}[
  colback=lightbg, colframe=primary!60,
  width=0.85\textwidth, arc=5pt,
  title={\bfseries\textcolor{primary}{Resumen Ejecutivo}},
  fonttitle=\normalsize
]
ChatHCE es un sistema de an\'alisis cl\'inico inteligente dise\~nado para profesionales de urgencias hospitalarias. Integra inteligencia artificial conversacional con capacidades de Retrieval-Augmented Generation (RAG) para el an\'alisis de datos m\'edicos del dataset MIMIC-IV-ED (222 pacientes, 6 tablas). El sistema implementa una arquitectura multiagente orquestada por Claude Haiku~4.5 (Anthropic) que coordina tres herramientas especializadas: consulta a base de datos PostgreSQL, b\'usqueda sem\'antica h\'ibrida en documentos cl\'inicos, y generaci\'on din\'amica de visualizaciones con Plotly. La arquitectura incorpora mecanismos de seguridad multicapa (validaci\'on SQL, detecci\'on de tautolog\'ias, rate limiting, RLS), un sistema anti-alucinaci\'on con directivas expl\'icitas, y un pipeline RAG avanzado con chunking jer\'arquico padre-hijo, b\'usqueda h\'ibrida vectorial-l\'exica y reranking por cross-encoder. La evaluaci\'on emp\'irica demuestra latencias inferiores a 8\,ms en todas las categor\'ias, 27/28 casos de prueba funcionales superados, y 12/13 pruebas de seguridad aprobadas.
\end{tcolorbox}
\vfill
{\small\textcolor{gray}{Sistema de An\'alisis Cl\'inico Inteligente para Urgencias Hospitalarias\\
Dataset: MIMIC-IV-ED Demo v2.2 \quad$\bullet$\quad Backend: Supabase PostgreSQL + pgvector\\
Modelo Principal: Claude Haiku 4.5 (\texttt{claude-haiku-4-5-20251001})}}
\end{titlepage}

\tableofcontents
\newpage

% ============================================================================
\section{Introducci\'on}
% ============================================================================

ChatHCE es una plataforma de an\'alisis cl\'inico dise\~nada para profesionales de urgencias que necesitan acceso r\'apido e inteligente a datos de pacientes, gu\'ias cl\'inicas y visualizaciones m\'edicas. El sistema opera sobre el dataset MIMIC-IV-ED (\textit{Medical Information Mart for Intensive Care IV -- Emergency Department}), un conjunto de datos completamente anonimizado de 222 pacientes de urgencias hospitalarias, organizado en 6 tablas relacionales.

El sistema se fundamenta en tres pilares tecnol\'ogicos convergentes:

\begin{enumerate}
  \item \textbf{Agente conversacional Claude Haiku 4.5}: Modelo de lenguaje de Anthropic con capacidad de \textit{tool-calling} nativo, que analiza la intenci\'on del usuario y selecciona autom\'aticamente las herramientas apropiadas para cada consulta.
  \item \textbf{Pipeline RAG avanzado}: Sistema de Retrieval-Augmented Generation con b\'usqueda h\'ibrida vectorial-l\'exica (pgvector + tsvector), chunking jer\'arquico padre-hijo, y reranking por cross-encoder, almacenado en Supabase pgvector.
  \item \textbf{Motor de visualizaci\'on template-first}: Generaci\'on din\'amica de gr\'aficas interactivas con Plotly, con selecci\'on autom\'atica de plantillas y ejecuci\'on segura en sandbox.
\end{enumerate}

La interfaz principal es un chat unificado construido con Streamlit que permite al usuario interactuar en lenguaje natural en espa\~nol, delegando al agente la selecci\'on y coordinaci\'on de las herramientas apropiadas.

\begin{table}[H]
\centering
\caption{Resumen de capacidades del sistema ChatHCE.}
\label{tab:capacidades}
\begin{tabularx}{\textwidth}{lXl}
\toprule
\textbf{Capacidad} & \textbf{Descripci\'on} & \textbf{Tecnolog\'ia} \\
\midrule
Consulta de pacientes & Acceso a datos de urgencias: signos vitales, diagn\'osticos, medicamentos, estancias & Supabase PostgreSQL \\
\addlinespace
B\'usqueda cl\'inica & Recuperaci\'on sem\'antica en gu\'ias y protocolos m\'edicos indexados & pgvector + tsvector \\
\addlinespace
Visualizaci\'on & Generaci\'on autom\'atica de gr\'aficas interactivas m\'edicas & Plotly / Matplotlib \\
\addlinespace
Chat unificado & Interfaz \'unica con selecci\'on autom\'atica de herramientas & LangChain + Claude \\
\addlinespace
Anti-alucinaci\'on & Directivas expl\'icitas para prevenir fabricaci\'on de datos m\'edicos & Prompt Engineering \\
\addlinespace
Seguridad SQL & Validaci\'on multicapa de consultas con detecci\'on de inyecci\'on & Python + Regex \\
\addlinespace
Autenticaci\'on & Gesti\'on de usuarios y sesiones con JWT & Supabase Auth \\
\addlinespace
Rate limiting & Protecci\'on contra abuso con ventana deslizante & Python (Singleton) \\
\bottomrule
\end{tabularx}
\end{table}

% ============================================================================
\section{Arquitectura General del Sistema}
% ============================================================================

\subsection{Arquitectura por Capas}

El sistema sigue una arquitectura de cinco capas con separaci\'on estricta de responsabilidades. Cada capa expone interfaces bien definidas hacia las capas adyacentes, garantizando modularidad, testabilidad y escalabilidad independiente.

\begin{figure}[H]
\centering
\begin{tikzpicture}[node distance=0.15cm]

% Capa 1 - Presentacion
\node[layerbox=blue, minimum width=13cm, minimum height=1.6cm] (L1) at (0,0) {};
\node[font=\footnotesize\sffamily\bfseries, text=blue!70, anchor=west] at ([xshift=6pt]L1.west) {Capa 1: Presentaci\'on};
\node[tblbox=blue, minimum width=2.8cm] at (-3.8,0) {\texttt{main.py}\\Streamlit App};
\node[tblbox=blue, minimum width=3.2cm] at (-0.2,0) {\texttt{unified\_chat\_interface.py}\\Chat UI};
\node[tblbox=blue, minimum width=2.4cm] at (3.2,0) {\texttt{components/}\\Sidebar/Auth};
\node[tblbox=blue, minimum width=2.4cm] at (5.8,0) {Document\\Manager};

% Capa 2 - Aplicacion
\node[layerbox=teal, minimum width=13cm, minimum height=1.6cm] (L2) at (0,-2.1) {};
\node[font=\footnotesize\sffamily\bfseries, text=teal!70, anchor=west] at ([xshift=6pt]L2.west) {Capa 2: Aplicaci\'on};
\node[tblbox=teal, minimum width=3.5cm] at (-3.2,-2.1) {\texttt{unified\_agent.py}\\UnifiedChatAgent};
\node[tblbox=teal, minimum width=3cm] at (0.8,-2.1) {\texttt{prompt\_manager.py}\\PromptManager};
\node[tblbox=teal, minimum width=3cm] at (4.5,-2.1) {\texttt{llm\_manager.py}\\ClaudeLLMManager};

% Capa 3 - Herramientas
\node[layerbox=orange, minimum width=13cm, minimum height=1.6cm] (L3) at (0,-4.2) {};
\node[font=\footnotesize\sffamily\bfseries, text=orange!70, anchor=west] at ([xshift=6pt]L3.west) {Capa 3: Herramientas};
\node[tblbox=orange, minimum width=2.8cm] at (-4,-4.2) {\texttt{database\_tool.py}\\Database Tool};
\node[tblbox=orange, minimum width=2.8cm] at (-0.5,-4.2) {\texttt{rag\_tool.py}\\RAG Tool};
\node[tblbox=orange, minimum width=3cm] at (3.2,-4.2) {\texttt{viz\_collaboration.py}\\Visualization Tool};
\node[tblbox=orange, minimum width=2.2cm] at (6,-4.2) {\texttt{claude\_adapter.py}\\Adapter};

% Capa 4 - Servicios
\node[layerbox=purple, minimum width=13cm, minimum height=1.6cm] (L4) at (0,-6.3) {};
\node[font=\footnotesize\sffamily\bfseries, text=purple!70, anchor=west] at ([xshift=6pt]L4.west) {Capa 4: Servicios};
\node[tblbox=purple, minimum width=2.2cm] at (-4.8,-6.3) {Database\\Service};
\node[tblbox=purple, minimum width=2.4cm] at (-2.2,-6.3) {Improved\\RAG Service};
\node[tblbox=purple, minimum width=2.2cm] at (0.4,-6.3) {Visualization\\Agent};
\node[tblbox=purple, minimum width=2cm] at (2.8,-6.3) {Cache\\Manager};
\node[tblbox=purple, minimum width=2cm] at (5,-6.3) {Rate\\Limiter};
\node[tblbox=purple, minimum width=2cm] at (6.8,-6.3) {Conn.\\Pool};

% Capa 5 - Datos
\node[layerbox=red, minimum width=13cm, minimum height=1.6cm] (L5) at (0,-8.4) {};
\node[font=\footnotesize\sffamily\bfseries, text=red!70, anchor=west] at ([xshift=6pt]L5.west) {Capa 5: Datos};
\node[tblbox=red, minimum width=3.5cm] at (-3.8,-8.4) {Supabase PostgreSQL\\(MIMIC-IV-ED)};
\node[tblbox=red, minimum width=3.5cm] at (0.5,-8.4) {Supabase pgvector\\(Embeddings RAG)};
\node[tblbox=red, minimum width=3cm] at (4.5,-8.4) {File Storage\\(Documentos)};

% Flechas
\draw[arrow] (L1.south) -- (L2.north);
\draw[arrow] (L2.south) -- (L3.north);
\draw[arrow] (L3.south) -- (L4.north);
\draw[arrow] (L4.south) -- (L5.north);

\end{tikzpicture}
\caption{Arquitectura por capas del sistema ChatHCE. Cada capa encapsula responsabilidades espec\'ificas con interfaces bien definidas.}
\label{fig:capas}
\end{figure}

\begin{table}[H]
\centering
\caption{Descripci\'on de las cinco capas arquitect\'onicas.}
\label{tab:capas}
\begin{tabularx}{\textwidth}{llX}
\toprule
\textbf{Capa} & \textbf{Nombre} & \textbf{Responsabilidades y archivos principales} \\
\midrule
1 & Presentaci\'on & Interfaz Streamlit, chat interactivo, autenticaci\'on, gesti\'on de documentos. \texttt{main.py}, \texttt{ui/unified\_chat\_interface.py}, \texttt{ui/components/} \\
\addlinespace
2 & Aplicaci\'on & Orquestaci\'on del agente, an\'alisis de intenci\'on, selecci\'on de herramientas, s\'intesis de respuestas. \texttt{services/unified\_chat/unified\_agent.py} \\
\addlinespace
3 & Herramientas & Tres herramientas especializadas adaptadas al formato Claude. \texttt{services/unified\_chat/tools/} \\
\addlinespace
4 & Servicios & Acceso a datos, pipeline RAG, visualizaci\'on, cach\'e, rate limiting, pool de conexiones. \texttt{services/} \\
\addlinespace
5 & Datos & Supabase PostgreSQL (MIMIC-IV-ED), pgvector (embeddings), almacenamiento de archivos. \\
\bottomrule
\end{tabularx}
\end{table}

\subsection{Flujo de Procesamiento Principal}

La Figura~\ref{fig:flujo} muestra el flujo completo desde la consulta del usuario hasta la respuesta integrada, incluyendo la selecci\'on autom\'atica de herramientas y la s\'intesis final.

\begin{figure}[H]
\centering
\begin{tikzpicture}[node distance=0.55cm]

\node[io] (input) {Consulta del usuario (lenguaje natural)};
\node[servicebox, below=of input] (rl) {Rate Limiter + Validaci\'on de entrada};
\node[servicebox, below=of rl] (cache) {Cache Manager (verificar hit)};
\node[process, below=of cache] (agent) {Claude Haiku 4.5\\analiza intenci\'on y selecciona herramientas};
\node[decision, below=0.7cm of agent] (select) {Herramientas\\necesarias};

\node[dbbox, below left=0.8cm and 1.8cm of select] (db) {Database\\Tool};
\node[ragbox, below=0.8cm of select] (rag) {RAG\\Tool};
\node[vizbox, below right=0.8cm and 1.8cm of select] (viz) {Visualization\\Tool};

\node[process, below=2.2cm of select] (synth) {Claude sintetiza respuesta integrada\\(datos + gu\'ias + gr\'aficas + fuentes)};
\node[servicebox, below=of synth] (cacheset) {Cache Manager (guardar respuesta)};
\node[io, below=of cacheset] (output) {Respuesta: texto + gr\'aficas + fuentes citadas};

\draw[arrow] (input) -- (rl);
\draw[arrow] (rl) -- (cache);
\draw[arrow] (cache) -- (agent);
\draw[arrow] (agent) -- (select);
\draw[arrow, color=dbcolor] (select) -| (db);
\draw[arrow, color=ragcolor] (select) -- (rag);
\draw[arrow, color=vizcolor] (select) -| (viz);
\draw[arrow, color=dbcolor] (db) |- (synth);
\draw[arrow, color=ragcolor] (rag) -- (synth);
\draw[arrow, color=vizcolor] (viz) |- (synth);
\draw[arrow] (synth) -- (cacheset);
\draw[arrow] (cacheset) -- (output);

% Etiquetas
\node[label, right=0.1cm of rl] {30/min, 300/hora, burst=5/10s};
\node[label, right=0.1cm of cache] {TTL=300s, LRU eviction};
\node[label, right=0.1cm of agent] {max\_iterations=5, timeout=120s};

\end{tikzpicture}
\caption{Flujo completo de procesamiento de una consulta en ChatHCE. El agente selecciona autom\'aticamente las herramientas necesarias y sintetiza una respuesta integrada.}
\label{fig:flujo}
\end{figure}

\subsection{Patrones de Dise\~no Implementados}

\begin{table}[H]
\centering
\caption{Patrones de dise\~no implementados en ChatHCE.}
\label{tab:patrones}
\begin{tabularx}{\textwidth}{llXl}
\toprule
\textbf{Patr\'on} & \textbf{Componente} & \textbf{Prop\'osito} & \textbf{Archivo} \\
\midrule
Adapter & \texttt{ClaudeToolAdapter} & Adapta herramientas al formato de tool-calling de Claude/LangChain & \texttt{claude\_adapter.py} \\
\addlinespace
Strategy & \texttt{SearchStrategy} & Diferentes estrategias de b\'usqueda RAG (similarity, MMR, hybrid) & \texttt{improved\_rag\_service.py} \\
\addlinespace
Singleton & \texttt{CacheManager} & Instancia \'unica de cach\'e compartida entre todos los componentes & \texttt{cache\_manager.py} \\
\addlinespace
Singleton & \texttt{RateLimiter} & Estado compartido de rate limiting entre requests & \texttt{rate\_limiter.py} \\
\addlinespace
Singleton & \texttt{ImprovedRAGService} & Evita recarga del modelo CUDA en re-runs de Streamlit & \texttt{improved\_rag\_service.py} \\
\addlinespace
Factory & \texttt{create\_*\_tool()} & Funciones de f\'abrica para instanciar herramientas & \texttt{tools/} \\
\addlinespace
Decorator & \texttt{@retry\_on\_failure} & Reintentos con backoff exponencial en operaciones de BD & \texttt{database\_service.py} \\
\addlinespace
Decorator & \texttt{@track\_performance} & Monitoreo autom\'atico de rendimiento en operaciones cr\'iticas & \texttt{agent\_performance\_monitor.py} \\
\addlinespace
Observer & \texttt{PerformanceMonitor} & Monitoreo de m\'etricas y alertas de rendimiento & \texttt{agent\_performance\_monitor.py} \\
\addlinespace
Chain of Resp. & Fallback LLM & Cadena Haiku $\to$ Sonnet $\to$ Opus para alta disponibilidad & \texttt{llm\_manager.py} \\
\bottomrule
\end{tabularx}
\end{table}

"""

with open("latex_files/arquitectura_chathce.tex", "w", encoding="utf-8") as f:
    f.write(PART1)
print("Part 1 written:", len(PART1), "chars")
