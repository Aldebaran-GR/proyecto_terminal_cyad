\NeedsTeXFormat{LaTeX2e}
\LoadClass[12pt, letterpaper]{article}
\pdfminorversion 4
%Para no resaltar las ligas
\RequirePackage[hidelinks]{hyperref}

\RequirePackage{listings,xcolor}
%Verbatim con soporte UTF-8 (fancyvrb) para el apéndice de código
\RequirePackage{fancyvrb}
%Permite usar _ en texto sin escapar
\RequirePackage{underscore}

%Determinar el tamaño del papel y el margen
\RequirePackage[letterpaper, margin=1in]{geometry}

%Necesarias para usar tablas de varias páginas y líneas de separación
\RequirePackage{longtable}
\RequirePackage{booktabs}

%Necesario para incluir gráficas
\RequirePackage{graphicx} 

\RequirePackage{ragged2e}

%Para utilizar diagramas de Gantt
\RequirePackage{pgfgantt}

%Para diagramas nativos en LaTeX (arquitectura, casos de uso, ER)
\RequirePackage{tikz}
\usetikzlibrary{positioning,shapes.geometric,arrows.meta,shadows,fit,backgrounds,calc}

%Para el resaltado en amarillo de las modificaciones
\RequirePackage{soul}
%\RequirePackage{soulutf8}

%Para colocar las notas al pie de página al final sin importar que quede espacio vacío
\RequirePackage[bottom]{footmisc}
\RequirePackage{etoolbox}
\RequirePackage{ifthen}

%Para el tipo tamaño de las letras en section y subsection
\RequirePackage{titlesec}
\titleformat*{\section}{\large\bfseries}
\titleformat*{\subsection}{\normalsize\bfseries}
\RequirePackage{palatino} %Tipo

%Para indicar que se usará Figura y Tabla en español, además, se coloca como separador un punto
\RequirePackage{caption}
\captionsetup[figure]{name={Figura },labelsep=period}
\captionsetup[table]{name={Tabla },labelsep=period}

%Utilizar el idioma español en la fecha
\RequirePackage[spanish]{babel}
\RequirePackage{soul,color}
\RequirePackage{enumitem}

\RequirePackage[T1]{fontenc}
\graphicspath{{./Imagenes/}}
%\small UAM-Azcapotzalco
\RequirePackage{fancyhdr}
\fancyhead{}
\fancyhead[L]{\footnotesize \fontfamily{qtm}\selectfont Reporte de Proyecto de Integración}
\fancyhead[R]{\footnotesize \fontfamily{qtm}\selectfont Ingeniería en Computación}
\fancyfoot{} % clear all footer fields
\fancyfoot[R]{\footnotesize\fontfamily{qtm}\selectfont \thepage}
\fancyfoot[L]{\footnotesize \fontfamily{qtm}\selectfont UAM-Azcapotzalco}
\fancyfoot[C]{}


\definecolor{codegreen}{rgb}{0,0.6,0}
\definecolor{codegray}{rgb}{0.5,0.5,0.5}
\definecolor{codepurple}{rgb}{0.58,0,0.82}
\definecolor{backcolour}{rgb}{0.95,0.95,0.92}

\lstdefinestyle{mystyle}{
	backgroundcolor=\color{backcolour},
	commentstyle=\color{codegreen},
	keywordstyle=\color{magenta},
	numberstyle=\tiny\color{codegray},
	stringstyle=\color{codepurple},
	basicstyle=\ttfamily\footnotesize,
	breakatwhitespace=false,
	breaklines=true,
	captionpos=b,
	keepspaces=true,
	numbers=left,
	numbersep=5pt,
	showspaces=false,
	showstringspaces=false,
	showtabs=false,
	tabsize=2,
	inputencoding=utf8,
	extendedchars=true,
	literate=%
	    {á}{{\'a}}1 {é}{{\'e}}1 {í}{{\'i}}1 {ó}{{\'o}}1 {ú}{{\'u}}1
	    {Á}{{\'A}}1 {É}{{\'E}}1 {Í}{{\'I}}1 {Ó}{{\'O}}1 {Ú}{{\'U}}1
	    {ñ}{{\~n}}1 {Ñ}{{\~N}}1 {ü}{{\"u}}1 {Ü}{{\"U}}1
	    {¿}{{?`}}1 {¡}{{!`}}1
}

\lstdefinestyle{mystyle2}
{
	language=[LaTeX]{TeX},
	texcsstyle=*\color{blue},
	basicstyle=\ttfamily,
	moretexcs={mycommand}, % user command highlight
	frame=single,
}

\lstset{style=mystyle2,inputencoding=utf8,extendedchars=true}


\def\version#1{\def\@version{#1}}
\def\trimestre#1{\def\@trimestre{#1}}
\def\tipo#1{\def\@tipo{#1}}
\def\matricula#1{\def\@matricula{#1}}
\def\alumno#1{\def\@alumno{#1}}
\def\titulo#1{\def\@titulo{#1}}


\def\asesor#1{\def\@asesor{#1}}
\def\categoria#1{\def\@categoria{#1}}
\def\departamento#1{\def\@departamento{#1}}
\def\correo#1{\def\@correo{#1}}

\def\coasesor#1{\def\@coasesor{#1}}
\def\categoriacoasesor#1{\def\@categoriacoasesor{#1}}
\def\departamentocoasesor#1{\def\@departamentocoasesor{#1}}
\def\correocoasesor#1{\def\@correocoasesor{#1}}

\def\introduccion#1{\def\@introduccion{#1}}

%Muestra la captura si existe; si no, un placeholder visible.
%Uso: \captura[ancho]{nombre_archivo_sin_extension}
\newcommand{\captura}[2][0.9\textwidth]{%
    \IfFileExists{./Imagenes/#2.png}%
        {\includegraphics[width=#1]{#2}}%
        {\IfFileExists{./Imagenes/#2.pdf}%
            {\includegraphics[width=#1]{#2}}%
            {\IfFileExists{./Imagenes/#2.jpg}%
                {\includegraphics[width=#1]{#2}}%
                {\fbox{\begin{minipage}[c][6cm][c]{#1}\centering\itshape\small Captura pendiente: \texttt{#2}\end{minipage}}}}}%
}

\bibliographystyle{IEEEtran}

\newcommand{\portada}{\maketitle}

\newcommand{\referencias}{\bibliography{./Referencias/piic.bib} }

\newcommand{\responsabilidad}{\resp}

\newcommand{\intro}{
	\setcounter{page}{1}
	\pagestyle{fancy}
	\section{Introducción}
	\justifying\@introduccion
	
}

\newcommand{\resp}{
	\ifthenelse{\equal{\@coasesor}{\empty }}
	%Este texto SÍ debe incluirse para que la propuesta pueda ser aceptada (con el ajuste mencionado en género y número de asesores).
	{El/La asesor(a) se responsabiliza de guiar al alumno y de que todos los recursos mencionados en la Factibilidad Técnica estarán disponibles para el alumno, de modo que el proyecto de integración se pueda concluir en tiempo y forma.\\[2.5cm]
	%Cerrar esta sección con una conclusión
	\begin{center}
		\begin{minipage}{0.45\textwidth}
			\centering
			\@asesor %grado y nombre completo del asesor
		\end{minipage}
	\end{center}}
	{Las/Los asesoras(es) se responsabilizan de guiar al alumno y de que todos los recursos mencionados en la Factibilidad Técnica estarán disponibles para el alumno, de modo que el proyecto de integración se pueda concluir en tiempo y forma.\\[2.5cm]
	%Cerrar esta sección con una conclusión
	\begin{center}
		\begin{minipage}{0.45\textwidth}
			\centering
			\@asesor %grado y nombre completo del asesor
		\end{minipage}
	\begin{minipage}{0.45\textwidth}
		\centering
		\@coasesor %grado y nombre completo del asesor
	\end{minipage}
\end{center}}
}

\newcommand{\asesores}[8]{
		\ifthenelse{\equal{#5}{\empty }}
	{\begin{minipage}{0.45\linewidth}
			\centering
			#1\\%Grado y nombre del asesor
			#2\\%Categoría del asesor, e.g. Profesor Titular, Profesor Asociado
			#3\\%Departamento, e.g. Departamento de Sistemas
			\href{mailto:#4}{#4}%Correo del asesor
	\end{minipage}\\[2.5cm]
	}
	{\begin{minipage}{0.45\linewidth}
			\centering
			#1\\%Grado y nombre del asesor
			#2\\%Categoría del asesor, e.g. Profesor Titular, Profesor Asociado
			#3\\%Departamento, e.g. Departamento de Sistemas
			\href{mailto:#4}{#4}%Correo del asesor
		\end{minipage}
		\begin{minipage}{0.45\linewidth}
			\centering
			#5\\%Grado y nombre del asesor
			#6\\%Categoría del asesor, e.g. Profesor Titular, Profesor Asociado
			#7\\%Departamento, e.g. Departamento de Sistemas
			\href{mailto:#8}{#8}%Correo del asesor
		\end{minipage}\\[2.5cm] 
	}%
}


\newcommand{\asesoresp}[2]{
	\ifthenelse{\equal{#2}{\empty }}
	{	\centering
		\begin{minipage}{0.45\linewidth}
			\centering
			#1\\%Grado y nombre del asesor
		\end{minipage}\\[2.5cm]
	}
	{\begin{minipage}{0.45\linewidth}
			\centering
			#1\\%Grado y nombre del asesor
		\end{minipage}
		\begin{minipage}{0.45\linewidth}
			\centering
			#2\\%Grado y nombre del asesor
		\end{minipage}\\[2.5cm] 
	}%
}



\newcommand{\declaratoria}[1]{
	\ifthenelse{\equal{#1}{Experiencia Profesional}}
	{\noindent \small Esta propuesta es solo para aprobar el Seminario de Integración en Ingeniería en Computación.}
	{ }%
}

\makeatletter         
\renewcommand\maketitle{
	{\raggedright % Note the extra {
			\begin{titlepage}
			\vspace*{\fill} %Centra el contenido de la página verticalmente
			\center % Centra todo el contenido de la página horizontalmente
			\fontfamily{bch}\selectfont
			%-------------------------------------------------------------------------------
			%	Encabezado de la portada
			%-------------------------------------------------------------------------------
			\includegraphics[width=0.9\textwidth]{banner}
			\vspace{2.5cm}
			
			%-------------------------------------------------------------------------------
			%	Título
			%-------------------------------------------------------------------------------
			
			{\Large\textbf{\fontfamily{qtm}\selectfont{\@titulo}}}\\[0.2cm]
			%Modifica esta frase para que se ajuste al número de revisión que corresponda
			\@tipo\\[0.2cm]
			\@version\\[0.2cm]
			Trimestre \@trimestre \\[2.5cm] %Modifica el año y el período
			
			%-------------------------------------------------------------------------------
			%	Autor
			%-------------------------------------------------------------------------------
			\@alumno\\ %Tu nombre
			\@matricula\\%Tu matrícula
			\href{mailto:al\@matricula @azc.uam.mx}{al\@matricula @azc.uam.mx}\\%Tu correo electrónico 
			[3.5cm] %Espacio antes de los datos de asesores.
			
			
			%-------------------------------------------------------------------------------
			%	Asesores
			%-------------------------------------------------------------------------------
			\asesores{\@asesor}{\@categoria}{\@departamento}{\@correo}{\@coasesor}{\@categoriacoasesor}{\@departamentocoasesor}{\@correocoasesor}
			
			%-------------------------------------------------------------------------------
			%	Fecha de entrega
			%-------------------------------------------------------------------------------
			\textspanish{\today}
			
			\vfill %Rellena el espacio sobrante con espacios en blanco
			\vspace*{\fill}
\end{titlepage}

\thispagestyle{empty}
\section*{\centering Declaratoria}

\noindent\justifying Yo, César Benavides Álvarez, declaro que aprobé el contenido del presente Reporte de Proyecto de Integración y doy mi autorización para su publicación en la Biblioteca Digital, así como en el Repositorio Institucional de la UAM Azcapotzalco.\\[1.8cm]

{\centering César Benavides Álvarez\par}
\vspace{1.6cm}

\noindent\justifying Yo, Josué Figueroa González, declaro que aprobé el contenido del presente Reporte de Proyecto de Integración y doy mi autorización para su publicación en la Biblioteca Digital, así como en el Repositorio Institucional de la UAM Azcapotzalco.\\[1.8cm]

{\centering Josué Figueroa González\par}
\vspace{1.6cm}

\noindent\justifying Yo, Zuriel Godinez Ramos, doy mi autorización a la Coordinación de Servicios de Información de la Universidad Autónoma Metropolitana, Unidad Azcapotzalco, para publicar el presente documento en la Biblioteca Digital, así como en el Repositorio Institucional de la UAM Azcapotzalco. En caso de que el Comité de Estudios de la Licenciatura en Ingeniería en Computación apruebe la realización de la presente propuesta, otorgamos nuestra autorización para su publicación en la página de la División de Ciencias Básicas e Ingeniería.\\[1.8cm]

{\centering Zuriel Godinez Ramos\par}

\vfill
%Este párrafo es solo si van a presentar su propuesta en la modalidad de Experiencia profesional
\declaratoria{\@tipo}
%En caso contrario, eliminar este párrafo

\newpage


}} % Note the extra }
\makeatother
