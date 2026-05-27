export type IconEntry = { key: string; label: string; paths: string[]; fill?: boolean };

export const ICONS: IconEntry[] = [
  // Media
  { key: "play",         label: "Play",          fill: true,  paths: ["M5 3l14 9-14 9V3z"] },
  { key: "pause",        label: "Pause",          fill: true,  paths: ["M6 4h4v16H6z", "M14 4h4v16h-4z"] },
  { key: "skip-forward", label: "Skip Forward",              paths: ["M5 4l9 8-9 8V4z", "M19 5v14"] },
  { key: "skip-back",    label: "Skip Back",                 paths: ["M19 4L10 12l9 8V4z", "M5 5v14"] },
  { key: "volume-2",     label: "Volume",                    paths: ["M11 5L6 9H2v6h4l5 4V5z", "M15.54 8.46a5 5 0 010 7.07", "M19.07 4.93a10 10 0 010 14.14"] },
  { key: "volume-x",     label: "Mute",                      paths: ["M11 5L6 9H2v6h4l5 4V5z", "M23 9l-6 6M17 9l6 6"] },
  { key: "mic",          label: "Microphone",                paths: ["M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z", "M19 10v2a7 7 0 01-14 0v-2", "M12 19v4", "M8 23h8"] },
  { key: "music",        label: "Music",                     paths: ["M9 18V5l12-2v13", "M6 21a3 3 0 100-6 3 3 0 000 6z", "M18 19a3 3 0 100-6 3 3 0 000 6z"] },
  { key: "headphones",   label: "Headphones",                paths: ["M3 18v-6a9 9 0 0118 0v6", "M3 18a2 2 0 004 0v-3a2 2 0 00-4 0v3z", "M17 18a2 2 0 004 0v-3a2 2 0 00-4 0v3z"] },
  { key: "radio",        label: "Radio",                     paths: ["M4.9 19.1C1 15.2 1 8.8 4.9 4.9", "M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5", "M12 12h.01"] },

  // System
  { key: "power",        label: "Power",                     paths: ["M18.36 6.64a9 9 0 11-12.73 0", "M12 2v10"] },
  { key: "settings",     label: "Settings",                  paths: ["M12 15a3 3 0 100-6 3 3 0 000 6z", "M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-2.35 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"] },
  { key: "refresh-cw",   label: "Refresh",                   paths: ["M23 4v6h-6", "M1 20v-6h6", "M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"] },
  { key: "trash-2",      label: "Trash",                     paths: ["M3 6h18", "M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a1 1 0 011-1h4a1 1 0 011 1v2", "M10 11v6", "M14 11v6"] },
  { key: "copy",         label: "Copy",                      paths: ["M20 9H11a2 2 0 00-2 2v9a2 2 0 002 2h9a2 2 0 002-2v-9a2 2 0 00-2-2z", "M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"] },
  { key: "lock",         label: "Lock",                      paths: ["M19 11H5a2 2 0 00-2 2v7a2 2 0 002 2h14a2 2 0 002-2v-7a2 2 0 00-2-2z", "M7 11V7a5 5 0 0110 0v4"] },
  { key: "zap",          label: "Zap",           fill: true,  paths: ["M13 2L3 14h9l-1 8 10-12h-9l1-8z"] },
  { key: "bell",         label: "Bell",                      paths: ["M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9", "M13.73 21a2 2 0 01-3.46 0"] },
  { key: "shield",       label: "Shield",                    paths: ["M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"] },
  { key: "search",       label: "Search",                    paths: ["M11 4a7 7 0 100 14A7 7 0 0011 4z", "M21 21l-4.35-4.35"] },
  { key: "alert-circle", label: "Alert",                     paths: ["M12 2a10 10 0 100 20A10 10 0 0012 2z", "M12 8v4", "M12 16h.01"] },

  // Apps
  { key: "globe",        label: "Globe",                     paths: ["M12 2a10 10 0 100 20A10 10 0 0012 2z", "M2 12h20", "M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"] },
  { key: "terminal",     label: "Terminal",                  paths: ["M4 17l6-6-6-6", "M12 19h8"] },
  { key: "code",         label: "Code",                      paths: ["M16 18l6-6-6-6", "M8 6l-6 6 6 6"] },
  { key: "camera",       label: "Camera",                    paths: ["M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z", "M12 17a4 4 0 100-8 4 4 0 000 8z"] },
  { key: "film",         label: "Film",                      paths: ["M19.82 2H4.18A2.18 2.18 0 002 4.18v15.64A2.18 2.18 0 004.18 22h15.64A2.18 2.18 0 0022 19.82V4.18A2.18 2.18 0 0019.82 2z", "M7 2v20", "M17 2v20", "M2 12h20"] },
  { key: "image",        label: "Image",                     paths: ["M19 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2z", "M8.5 10a1.5 1.5 0 100-3 1.5 1.5 0 000 3z", "M21 15l-5-5L5 21"] },
  { key: "file-text",    label: "File",                      paths: ["M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z", "M14 2v6h6", "M16 13H8", "M16 17H8", "M10 9H8"] },
  { key: "folder",       label: "Folder",                    paths: ["M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"] },
  { key: "download",     label: "Download",                  paths: ["M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4", "M7 10l5 5 5-5", "M12 15V3"] },
  { key: "upload",       label: "Upload",                    paths: ["M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4", "M17 8l-5-5-5 5", "M12 3v12"] },

  // Tech
  { key: "cpu",          label: "CPU",                       paths: ["M7 7h10v10H7z", "M9 2v5", "M15 2v5", "M9 17v5", "M15 17v5", "M2 9h5", "M2 15h5", "M17 9h5", "M17 15h5"] },
  { key: "database",     label: "Database",                  paths: ["M12 2C6.48 2 3 4.02 3 5v14c0 .98 3.48 3 9 3s9-2.02 9-3V5c0-.98-3.48-3-9-3z", "M3 5c0 .98 3.48 3 9 3s9-2.02 9-3", "M3 12c0 .98 3.48 3 9 3s9-2.02 9-3"] },
  { key: "activity",     label: "Activity",                  paths: ["M22 12h-4l-3 9L9 3l-3 9H2"] },
  { key: "git-branch",   label: "Branch",                    paths: ["M6 3v12", "M18 9a3 3 0 100-6 3 3 0 000 6z", "M6 21a3 3 0 100-6 3 3 0 000 6z", "M18 9a9 9 0 01-9 9"] },
  { key: "layers",       label: "Layers",                    paths: ["M12 2L2 7l10 5 10-5-10-5z", "M2 17l10 5 10-5", "M2 12l10 5 10-5"] },

  // Actions
  { key: "home",         label: "Home",                      paths: ["M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z", "M9 22V12h6v10"] },
  { key: "star",         label: "Star",          fill: true,  paths: ["M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"] },
  { key: "heart",        label: "Heart",                     paths: ["M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"] },
  { key: "bookmark",     label: "Bookmark",                  paths: ["M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"] },
  { key: "mail",         label: "Mail",                      paths: ["M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z", "M22 6l-10 7L2 6"] },
  { key: "check-circle", label: "Check",                     paths: ["M22 11.08V12a10 10 0 11-5.93-9.14", "M22 4L12 14.01l-3-3"] },
  { key: "plus-circle",  label: "Plus",                      paths: ["M12 2a10 10 0 100 20A10 10 0 0012 2z", "M12 8v8", "M8 12h8"] },
  { key: "arrow-right",  label: "Arrow Right",               paths: ["M5 12h14", "M12 5l7 7-7 7"] },
  { key: "edit-2",       label: "Edit",                      paths: ["M17 3a2.828 2.828 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z"] },
  { key: "external-link", label: "Open Link",                paths: ["M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6", "M15 3h6v6", "M10 14L21 3"] },
];
