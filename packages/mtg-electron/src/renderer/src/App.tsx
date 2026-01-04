import { useEffect, useState } from "react";

import {
  AppShell,
  Dashboard,
  SearchScreen,
  CollectionScreen,
  DecksScreen,
  DeckBuilderScreen,
  DeckSuggestionsScreen,
  SetsScreen,
  ArtistsScreen,
  SynergyFinderScreen,
  SettingsScreen,
  GalleryScreen,
  SplashScreen,
} from "./components";

import type { ReactNode } from "react";
import type { Screen } from "./components";
import type { ApiStatus } from "./components/StatusBar";

interface AppStats {
  cardCount: number;
  setCount: number;
  collectionCount: number;
  collectionValue: number;
}

const DEFAULT_STATS: AppStats = {
  cardCount: 35861,
  setCount: 1016,
  collectionCount: 0,
  collectionValue: 0,
};

function App(): ReactNode {
  const [isInitialized, setIsInitialized] = useState(false);
  const [currentScreen, setCurrentScreen] = useState<Screen>("dashboard");
  const [apiStatus, setApiStatus] = useState<ApiStatus>("starting");
  const [stats, setStats] = useState<AppStats>(DEFAULT_STATS);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null);
  const [galleryCardName, setGalleryCardName] = useState<string | null>(null);
  const [previousScreen, setPreviousScreen] = useState<Screen>("dashboard");

  useEffect(() => {
    // Only run after splash screen completes initialization
    if (!isInitialized) return;

    // Set API status to ready since splash screen verified it
    setApiStatus("ready");

    // Load collection stats
    window.electronAPI.collection.stats().then((collectionStats) => {
      if (!collectionStats.error) {
        setStats((prev) => ({
          ...prev,
          collectionCount: collectionStats.total,
        }));
      }
    });
  }, [isInitialized]);

  // Handle menu navigation and actions
  useEffect(() => {
    const handleNavigate = (screen: unknown): void => {
      if (typeof screen === "string") {
        // Map menu screen names to internal screen names
        const screenMap: Record<string, Screen> = {
          dashboard: "dashboard",
          search: "search",
          collection: "collection",
          decks: "decks",
          sets: "sets",
          synergies: "synergies",
          artists: "artists",
          "synergy-finder": "synergies",
          suggestions: "suggestions",
          settings: "settings",
        };
        const mappedScreen = screenMap[screen];
        if (mappedScreen) {
          setCurrentScreen(mappedScreen);
        }
      }
    };

    const handleAction = (action: unknown): void => {
      if (typeof action !== "string") return;

      switch (action) {
        case "import-collection":
          setCurrentScreen("collection");
          // TODO: Trigger import modal in CollectionScreen
          break;
        case "new-deck":
          setCurrentScreen("decks");
          // TODO: Trigger new deck creation
          break;
        case "focus-search":
          setCurrentScreen("search");
          // TODO: Focus search input
          break;
        case "go-back":
          // TODO: Implement navigation history
          break;
        case "go-forward":
          // TODO: Implement navigation history
          break;
      }
    };

    window.electronAPI.on("navigate", handleNavigate);
    window.electronAPI.on("action", handleAction);

    return (): void => {
      window.electronAPI.off("navigate", handleNavigate);
      window.electronAPI.off("action", handleAction);
    };
  }, []);

  const handleNavigate = (screen: Screen): void => {
    setPreviousScreen(currentScreen);
    setCurrentScreen(screen);
    // Clear search query when navigating away from search
    if (screen !== "search") {
      setSearchQuery("");
    }
    // Clear selected deck when navigating away from decks
    if (screen !== "decks") {
      setSelectedDeckId(null);
    }
    // Clear gallery card when navigating away from gallery
    if (screen !== "gallery") {
      setGalleryCardName(null);
    }
  };

  const handleOpenGallery = (cardName: string): void => {
    setPreviousScreen(currentScreen);
    setGalleryCardName(cardName);
    setCurrentScreen("gallery");
  };

  const handleBackFromGallery = (): void => {
    setGalleryCardName(null);
    setCurrentScreen(previousScreen);
  };

  const handleSelectDeck = (deckId: number): void => {
    setSelectedDeckId(deckId);
  };

  const handleBackFromDeckBuilder = (): void => {
    setSelectedDeckId(null);
  };

  const handleSearch = (query: string): void => {
    setSearchQuery(query);
    setCurrentScreen("search");
  };

  const renderScreen = (): ReactNode => {
    switch (currentScreen) {
      case "dashboard":
        return (
          <Dashboard
            onNavigate={handleNavigate}
            onSearch={handleSearch}
            cardCount={stats.cardCount}
            setCount={stats.setCount}
          />
        );
      case "search":
        return (
          <SearchScreen
            initialQuery={searchQuery}
            onOpenGallery={handleOpenGallery}
          />
        );
      case "collection":
        return <CollectionScreen />;
      case "artists":
        return <ArtistsScreen />;
      case "sets":
        return <SetsScreen onOpenGallery={handleOpenGallery} />;
      case "synergies":
        return <SynergyFinderScreen />;

      case "suggestions":
        return <DeckSuggestionsScreen />;
      case "decks":
        if (selectedDeckId !== null) {
          return (
            <DeckBuilderScreen
              deckId={selectedDeckId}
              onBack={handleBackFromDeckBuilder}
            />
          );
        }
        return <DecksScreen onSelectDeck={handleSelectDeck} />;
      case "settings":
        return <SettingsScreen />;

      case "gallery":
        if (galleryCardName) {
          return (
            <GalleryScreen
              cardName={galleryCardName}
              onBack={handleBackFromGallery}
            />
          );
        }
        return (
          <Dashboard
            onNavigate={handleNavigate}
            onSearch={handleSearch}
            cardCount={stats.cardCount}
            setCount={stats.setCount}
          />
        );
      default:
        return (
          <Dashboard
            onNavigate={handleNavigate}
            onSearch={handleSearch}
            cardCount={stats.cardCount}
            setCount={stats.setCount}
          />
        );
    }
  };

  // Show splash screen during initialization
  if (!isInitialized) {
    return <SplashScreen onReady={() => setIsInitialized(true)} />;
  }

  return (
    <AppShell
      currentScreen={currentScreen}
      onNavigate={handleNavigate}
      apiStatus={apiStatus}
      cardCount={stats.cardCount}
      setCount={stats.setCount}
      collectionCount={stats.collectionCount}
      collectionValue={stats.collectionValue}
    >
      {renderScreen()}
    </AppShell>
  );
}

export default App;
