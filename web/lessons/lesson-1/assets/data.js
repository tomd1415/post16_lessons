window.LESSON1_DATA = {
  "meta": {
    "title": "ICDL Thinking as a Coder 1.0 — Lesson 1 resources",
    "version": "1.0",
    "generated": "2026-01-07",
    "offline": true
  },
  "learningObjectives": [
    "Define computing.",
    "Define computational thinking.",
    "Describe typical computational thinking methods: decomposition, pattern recognition, abstraction, algorithms.",
    "Use decomposition to break down a complex problem into smaller parts.",
    "Define a program.",
    "Explain how algorithms are used in computational thinking.",
    "Identify patterns among smaller problems.",
    "Use abstraction to keep important details and drop irrelevant ones."
  ],
  "terms": [
    {
      "term": "Computing",
      "definition": "Doing calculations or processing data (often using computer systems)."
    },
    {
      "term": "Computational thinking",
      "definition": "Analysing a problem and working out a method to solve it in clear steps that people (and often computers) can follow."
    },
    {
      "term": "Decomposition",
      "definition": "Breaking a big problem into smaller, easier parts."
    },
    {
      "term": "Pattern recognition",
      "definition": "Spotting similarities or repetition between parts of a problem (or between different problems)."
    },
    {
      "term": "Abstraction",
      "definition": "Focusing on the important details and ignoring the irrelevant ones."
    },
    {
      "term": "Algorithm",
      "definition": "A precise step‑by‑step method (instructions/rules) to solve a problem or complete a task."
    },
    {
      "term": "Program",
      "definition": "An algorithm written in a form that a computer can run."
    },
    {
      "term": "Code",
      "definition": "The written instructions in a program."
    }
  ],
  "devices": [
    {
      "name": "Smartphone",
      "hint": "Has inputs/outputs and runs many programs."
    },
    {
      "name": "Washing machine",
      "hint": "Uses sensors and a control system to run cycles."
    },
    {
      "name": "Microwave",
      "hint": "Has programs (timers/power levels) and inputs."
    },
    {
      "name": "Toaster",
      "hint": "Usually simple control; some have sensors."
    },
    {
      "name": "Digital camera",
      "hint": "Processes image data; has inputs/outputs."
    },
    {
      "name": "Light bulb (basic)",
      "hint": "On/off only."
    },
    {
      "name": "Keyboard",
      "hint": "Input device only."
    },
    {
      "name": "Mouse",
      "hint": "Input device only."
    },
    {
      "name": "Calculator",
      "hint": "Processes numerical input using rules."
    },
    {
      "name": "Thermostat",
      "hint": "Reads temperature and controls heating."
    },
    {
      "name": "Traffic lights",
      "hint": "Timed/controlled sequences and sensors sometimes."
    },
    {
      "name": "Paper book",
      "hint": "No data processing."
    }
  ],
  "recipes": [
    {
      "title": "Chocolate cake (simplified)",
      "steps": [
        "Set oven temperature",
        "Mix ingredients",
        "Put mixture in tin",
        "Bake for a set time",
        "Check if baked; if not, wait and check again",
        "Remove from oven"
      ]
    },
    {
      "title": "Gingerbread men (simplified)",
      "steps": [
        "Set oven temperature",
        "Mix ingredients",
        "Roll and cut shapes",
        "Bake for a set time",
        "Check if done; if not, wait and check again",
        "Cool on rack"
      ]
    },
    {
      "title": "Blueberry muffins (simplified)",
      "steps": [
        "Set oven temperature",
        "Mix ingredients",
        "Fold in blueberries",
        "Spoon into cases",
        "Bake for a set time",
        "Remove and cool"
      ]
    }
  ],
  "abstractionPrompts": [
    {
      "title": "Organising a party",
      "question": "Select the details you must keep to plan the party (abstraction).",
      "items": [
        {
          "text": "Date",
          "keep": true
        },
        {
          "text": "Budget",
          "keep": true
        },
        {
          "text": "Venue",
          "keep": true
        },
        {
          "text": "Guest list",
          "keep": true
        },
        {
          "text": "Food allergies",
          "keep": true
        },
        {
          "text": "Colour of balloons",
          "keep": false
        },
        {
          "text": "Exact playlist order (before you know speakers)",
          "keep": false
        },
        {
          "text": "Font used on invitations",
          "keep": false
        }
      ],
      "explain": "A plan needs the essentials first. Decoration and cosmetic details can wait."
    },
    {
      "title": "Robo‑chef makes apple pie with ice cream",
      "question": "Select the information you must keep so the robo‑chef can succeed.",
      "items": [
        {
          "text": "Quantities/measurements of ingredients",
          "keep": true
        },
        {
          "text": "Oven temperature and time",
          "keep": true
        },
        {
          "text": "How to check ‘baked’ (test)",
          "keep": true
        },
        {
          "text": "Colour of the mixing bowl",
          "keep": false
        },
        {
          "text": "Brand of flour (if any flour works)",
          "keep": false
        },
        {
          "text": "Safety checks (hot surfaces, knives)",
          "keep": true
        },
        {
          "text": "Where ingredients are stored",
          "keep": true
        }
      ],
      "explain": "Abstraction removes irrelevant detail, but keeps what changes the outcome or safety."
    }
  ],
  "bigProblems": [
    {
      "title": "Global warming",
      "starter": "Break it down into smaller parts. Include at least one idea where software could help.",
      "exampleIdeas": [
        "Analyse household energy use to find easy savings",
        "Model transport routes to reduce emissions",
        "Monitor building temperature and heating efficiency"
      ]
    },
    {
      "title": "World peace",
      "starter": "Break it down into smaller parts. Include at least one practical software idea.",
      "exampleIdeas": [
        "Improve translation (text/voice) to reduce misunderstandings",
        "Identify misinformation patterns",
        "Model conflict drivers using data (carefully/ethically)"
      ]
    },
    {
      "title": "A colony on Mars",
      "starter": "Break it down into smaller parts. Include at least one software-supported idea.",
      "exampleIdeas": [
        "Model life-support inputs/outputs (water/air/food)",
        "Simulate habitat temperature and energy needs",
        "Optimise supply schedules and redundancy"
      ]
    }
  ],
  "quiz": {
    "title": "Lesson 1 check",
    "questions": [
      {
        "type": "mcq",
        "q": "Which is the best description of computing?",
        "options": [
          "Writing code only",
          "Processing data or performing calculations (often using computers)",
          "Using the internet",
          "Building hardware"
        ],
        "answer": 1,
        "why": "Computing is broader than coding; it’s about processing data and calculations."
      },
      {
        "type": "mcq",
        "q": "Which is NOT usually listed as a computational thinking method?",
        "options": [
          "Decomposition",
          "Pattern recognition",
          "Abstraction",
          "Apprehension"
        ],
        "answer": 3
      },
      {
        "type": "mcq",
        "q": "Decomposition means…",
        "options": [
          "Hiding important details",
          "Breaking a big problem into smaller parts",
          "Writing code with good indentation",
          "Guessing the answer quickly"
        ],
        "answer": 1
      },
      {
        "type": "mcq",
        "q": "An algorithm is…",
        "options": [
          "A computer",
          "A step-by-step set of rules/instructions to complete a task",
          "A type of network cable",
          "A random guess"
        ],
        "answer": 1
      },
      {
        "type": "short",
        "q": "Give one example of pattern recognition in everyday life (1–2 sentences).",
        "keyPoints": [
          "Same invitation template with different names/addresses",
          "Same steps repeated across recipes",
          "Same rules used for multiple similar tasks"
        ]
      },
      {
        "type": "short",
        "q": "Explain abstraction in your own words (1–2 sentences).",
        "keyPoints": [
          "Keep important details, ignore irrelevant ones"
        ]
      }
    ]
  }
};
