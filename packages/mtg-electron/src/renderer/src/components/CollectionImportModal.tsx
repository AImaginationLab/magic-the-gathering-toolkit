import { useState, useCallback, useEffect } from "react";
import { colors } from "../theme";

import type { ReactNode } from "react";
import type { components } from "../../../shared/types/api-generated";

type ParsedCard =
  components["schemas"]["mtg_core__api__routes__collection__ParsedCard"];

interface CollectionCard {
  cardName: string;
  quantity: number;
  foilQuantity: number;
  setCode: string | null;
  setName: string | null;
  collectorNumber: string | null;
  addedAt: string;
  // Enriched data from card database
  colors: string[];
  typeLine: string | null;
  rarity: string | null;
  cmc: number;
  priceUsd: number | null;
  priceUsdFoil: number | null;
}

interface CollectionImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (text: string, mode: "replace" | "add") => void;
  existingCards?: CollectionCard[];
}

type ImportStep = "input" | "mode" | "preview" | "importing";
type ImportMode = "replace" | "add";

interface DiffEntry {
  cardName: string;
  setCode: string | null;
  collectorNumber: string | null;
  oldQuantity: number;
  newQuantity: number;
  change: "added" | "increased" | "unchanged";
}

function computeDiff(
  existing: CollectionCard[],
  incoming: ParsedCard[],
): DiffEntry[] {
  const diff: DiffEntry[] = [];
  const existingMap = new Map<string, CollectionCard>();

  // Build map of existing cards
  for (const card of existing) {
    const key =
      card.setCode && card.collectorNumber
        ? `${card.cardName.toLowerCase()}|${card.setCode}|${card.collectorNumber}`
        : card.cardName.toLowerCase();
    existingMap.set(key, card);
  }

  // Process incoming cards
  for (const card of incoming) {
    const cardName =
      card.card_name ??
      `${card.set_code?.toUpperCase()} #${card.collector_number}`;
    const key =
      card.set_code && card.collector_number
        ? `${cardName.toLowerCase()}|${card.set_code}|${card.collector_number}`
        : cardName.toLowerCase();

    const existing = existingMap.get(key);
    const incomingQty = card.quantity ?? 1;

    if (existing) {
      const oldQty = existing.quantity + existing.foilQuantity;
      const newQty = oldQty + incomingQty;
      diff.push({
        cardName,
        setCode: card.set_code ?? null,
        collectorNumber: card.collector_number ?? null,
        oldQuantity: oldQty,
        newQuantity: newQty,
        change: "increased",
      });
    } else {
      diff.push({
        cardName,
        setCode: card.set_code ?? null,
        collectorNumber: card.collector_number ?? null,
        oldQuantity: 0,
        newQuantity: incomingQty,
        change: "added",
      });
    }
  }

  // Sort: added first, then increased
  return diff.sort((a, b) => {
    if (a.change === "added" && b.change !== "added") return -1;
    if (a.change !== "added" && b.change === "added") return 1;
    return a.cardName.localeCompare(b.cardName);
  });
}

export function CollectionImportModal({
  isOpen,
  onClose,
  onImport,
  existingCards = [],
}: CollectionImportModalProps): ReactNode {
  const [step, setStep] = useState<ImportStep>("input");
  const [mode, setMode] = useState<ImportMode | null>(null);
  const [inputText, setInputText] = useState("");
  const [parsedCards, setParsedCards] = useState<ParsedCard[]>([]);
  const [parseError, setParseError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [diff, setDiff] = useState<DiffEntry[]>([]);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setStep("input");
      setMode(null);
      setInputText("");
      setParsedCards([]);
      setParseError(null);
      setDiff([]);
    }
  }, [isOpen]);

  const handleParse = useCallback(async () => {
    if (!inputText.trim()) {
      setParseError("Please enter some cards to import");
      return;
    }

    setIsLoading(true);
    setParseError(null);

    try {
      const result = await window.electronAPI.collection.parse(inputText);
      if (result.cards && result.cards.length > 0) {
        setParsedCards(result.cards);
        setStep("mode");
      } else {
        setParseError("No valid cards found in the input");
      }
    } catch (err) {
      setParseError(`Failed to parse: ${String(err)}`);
    } finally {
      setIsLoading(false);
    }
  }, [inputText]);

  const handleModeSelect = useCallback(
    (selectedMode: ImportMode) => {
      setMode(selectedMode);
      if (selectedMode === "add") {
        // Compute diff for add mode
        const computed = computeDiff(existingCards, parsedCards);
        setDiff(computed);
      }
      setStep("preview");
    },
    [existingCards, parsedCards],
  );

  const handleImport = useCallback(() => {
    if (!mode) return;
    setStep("importing");
    onImport(inputText, mode);
  }, [inputText, mode, onImport]);

  const handleBack = useCallback(() => {
    if (step === "preview") {
      setStep("mode");
      setMode(null);
    } else if (step === "mode") {
      setStep("input");
      setParsedCards([]);
    }
  }, [step]);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  if (!isOpen) return null;

  const totalCards = parsedCards.reduce((sum, c) => sum + (c.quantity ?? 1), 0);
  const uniqueCards = parsedCards.length;
  const foilCards = parsedCards.filter((c) => c.foil).length;
  const withPrinting = parsedCards.filter(
    (c) => c.set_code && c.collector_number,
  ).length;

  // Diff stats
  const addedCount = diff.filter((d) => d.change === "added").length;
  const increasedCount = diff.filter((d) => d.change === "increased").length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.8)" }}
      onClick={handleClose}
    >
      <div
        className="w-full max-w-2xl max-h-[80vh] flex flex-col rounded-lg overflow-hidden"
        style={{
          background: colors.void.deep,
          border: `1px solid ${colors.border.subtle}`,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4 border-b"
          style={{ borderColor: colors.border.subtle }}
        >
          <h2
            className="font-display text-lg"
            style={{ color: colors.text.bright }}
          >
            {step === "input" && "Import Cards"}
            {step === "mode" && "Choose Import Mode"}
            {step === "preview" &&
              (mode === "replace" ? "Replace Collection" : "Add to Collection")}
            {step === "importing" && "Importing..."}
          </h2>
          <button
            onClick={handleClose}
            className="w-8 h-8 flex items-center justify-center rounded hover:bg-white/10 transition-colors"
            style={{ color: colors.text.muted }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-5">
          {/* Step 1: Input */}
          {step === "input" && (
            <>
              <p className="text-sm mb-4" style={{ color: colors.text.muted }}>
                Paste your card list below. Supports multiple formats:
              </p>

              <div
                className="text-xs mb-4 p-3 rounded font-mono"
                style={{
                  background: colors.void.light,
                  border: `1px solid ${colors.border.subtle}`,
                  color: colors.text.dim,
                }}
              >
                <div className="mb-2">
                  <span style={{ color: colors.text.muted }}>
                    Simple format:
                  </span>
                </div>
                <div className="pl-3 mb-3">
                  4 Lightning Bolt
                  <br />
                  2x Sol Ring [M21]
                  <br />
                  Counterspell *foil*
                </div>

                <div className="mb-2">
                  <span style={{ color: colors.text.muted }}>
                    Set context format:
                  </span>
                </div>
                <div className="pl-3">
                  fin:
                  <br />
                  &nbsp;&nbsp;345
                  <br />
                  &nbsp;&nbsp;2 239
                  <br />
                  &nbsp;&nbsp;421 f<br />
                  mkm:
                  <br />
                  &nbsp;&nbsp;12
                  <br />
                  &nbsp;&nbsp;4x 56
                </div>
              </div>

              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Paste your card list here..."
                className="w-full h-48 p-3 font-mono text-sm resize-none"
                style={{
                  background: colors.void.light,
                  border: `1px solid ${colors.border.standard}`,
                  borderRadius: "4px",
                  color: colors.text.standard,
                  outline: "none",
                }}
              />

              {parseError && (
                <div
                  className="mt-3 p-3 rounded text-sm"
                  style={{
                    background: "rgba(255,85,85,0.1)",
                    border: "1px solid rgba(255,85,85,0.3)",
                    color: "#ff5555",
                  }}
                >
                  {parseError}
                </div>
              )}
            </>
          )}

          {/* Step 2: Mode Selection */}
          {step === "mode" && (
            <>
              <div
                className="grid grid-cols-4 gap-3 mb-6 p-4 rounded"
                style={{
                  background: colors.void.light,
                  border: `1px solid ${colors.border.subtle}`,
                }}
              >
                <div>
                  <div
                    className="text-2xl font-display"
                    style={{ color: colors.gold.standard }}
                  >
                    {totalCards}
                  </div>
                  <div className="text-xs" style={{ color: colors.text.muted }}>
                    Total Cards
                  </div>
                </div>
                <div>
                  <div
                    className="text-2xl font-display"
                    style={{ color: colors.mana.blue.color }}
                  >
                    {uniqueCards}
                  </div>
                  <div className="text-xs" style={{ color: colors.text.muted }}>
                    Unique Entries
                  </div>
                </div>
                <div>
                  <div
                    className="text-2xl font-display"
                    style={{ color: colors.rarity.mythic.color }}
                  >
                    {foilCards}
                  </div>
                  <div className="text-xs" style={{ color: colors.text.muted }}>
                    Foils
                  </div>
                </div>
                <div>
                  <div
                    className="text-2xl font-display"
                    style={{ color: colors.mana.green.color }}
                  >
                    {withPrinting}
                  </div>
                  <div className="text-xs" style={{ color: colors.text.muted }}>
                    With Printing
                  </div>
                </div>
              </div>

              <p className="text-sm mb-4" style={{ color: colors.text.muted }}>
                How would you like to import these {totalCards} cards?
              </p>

              <div className="grid grid-cols-2 gap-4">
                {/* Replace Option */}
                <button
                  onClick={() => handleModeSelect("replace")}
                  className="p-4 rounded text-left transition-all hover:scale-[1.02]"
                  style={{
                    background: colors.void.light,
                    border: `2px solid ${colors.border.subtle}`,
                  }}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center"
                      style={{ background: colors.mana.red.color }}
                    >
                      <svg
                        width="20"
                        height="20"
                        viewBox="0 0 16 16"
                        fill="white"
                      >
                        <path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41zm-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z" />
                        <path
                          fillRule="evenodd"
                          d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5.002 5.002 0 0 0 8 3zM3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9H3.1z"
                        />
                      </svg>
                    </div>
                    <div
                      className="font-display text-base"
                      style={{ color: colors.text.bright }}
                    >
                      Replace Collection
                    </div>
                  </div>
                  <p className="text-xs" style={{ color: colors.text.muted }}>
                    Clear your existing collection and start fresh with these{" "}
                    {totalCards} cards.
                    {existingCards.length > 0 && (
                      <span style={{ color: colors.mana.red.color }}>
                        {" "}
                        This will remove your current {
                          existingCards.length
                        }{" "}
                        cards.
                      </span>
                    )}
                  </p>
                </button>

                {/* Add Option */}
                <button
                  onClick={() => handleModeSelect("add")}
                  className="p-4 rounded text-left transition-all hover:scale-[1.02]"
                  style={{
                    background: colors.void.light,
                    border: `2px solid ${colors.border.subtle}`,
                  }}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center"
                      style={{ background: colors.mana.green.color }}
                    >
                      <svg
                        width="20"
                        height="20"
                        viewBox="0 0 16 16"
                        fill="white"
                      >
                        <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z" />
                      </svg>
                    </div>
                    <div
                      className="font-display text-base"
                      style={{ color: colors.text.bright }}
                    >
                      Add to Collection
                    </div>
                  </div>
                  <p className="text-xs" style={{ color: colors.text.muted }}>
                    Merge these cards with your existing collection. Quantities
                    will be combined for matching cards.
                  </p>
                </button>
              </div>
            </>
          )}

          {/* Step 3: Preview */}
          {step === "preview" && mode === "replace" && (
            <>
              <div
                className="mb-4 p-4 rounded"
                style={{
                  background: "rgba(255,85,85,0.1)",
                  border: "1px solid rgba(255,85,85,0.3)",
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="#ff5555"
                  >
                    <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z" />
                  </svg>
                  <span
                    className="font-display text-sm"
                    style={{ color: "#ff5555" }}
                  >
                    This will replace your entire collection
                  </span>
                </div>
                <p className="text-xs" style={{ color: colors.text.muted }}>
                  Your current {existingCards.length} cards will be removed and
                  replaced with {totalCards} new cards.
                </p>
              </div>

              <div
                className="text-xs font-display mb-2"
                style={{ color: colors.text.muted }}
              >
                New Collection Preview ({uniqueCards} unique cards)
              </div>
              <div
                className="max-h-64 overflow-auto rounded"
                style={{
                  background: colors.void.light,
                  border: `1px solid ${colors.border.subtle}`,
                }}
              >
                {parsedCards.map((card, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-3 px-3 py-2"
                    style={{
                      borderBottom:
                        idx < parsedCards.length - 1
                          ? `1px solid ${colors.border.subtle}`
                          : "none",
                    }}
                  >
                    <div
                      className="w-8 text-right font-mono text-sm"
                      style={{ color: colors.gold.standard }}
                    >
                      {card.quantity ?? 1}x
                    </div>
                    <div className="flex-1">
                      <div
                        className="font-display text-sm"
                        style={{ color: colors.text.standard }}
                      >
                        {card.card_name ?? (
                          <span style={{ color: colors.text.muted }}>
                            {card.set_code?.toUpperCase()} #
                            {card.collector_number}
                          </span>
                        )}
                      </div>
                      {card.set_code && card.card_name && (
                        <div
                          className="text-xs"
                          style={{ color: colors.text.dim }}
                        >
                          {card.set_code.toUpperCase()}
                          {card.collector_number &&
                            ` #${card.collector_number}`}
                        </div>
                      )}
                    </div>
                    {card.foil && (
                      <i
                        className="ms ms-dfc-spark"
                        style={{
                          fontSize: "14px",
                          color: colors.rarity.mythic.color,
                        }}
                      />
                    )}
                  </div>
                ))}
              </div>
            </>
          )}

          {step === "preview" && mode === "add" && (
            <>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div
                  className="p-3 rounded"
                  style={{
                    background: "rgba(0,255,0,0.1)",
                    border: "1px solid rgba(0,255,0,0.3)",
                  }}
                >
                  <div
                    className="text-2xl font-display"
                    style={{ color: colors.mana.green.color }}
                  >
                    +{addedCount}
                  </div>
                  <div className="text-xs" style={{ color: colors.text.muted }}>
                    New cards to add
                  </div>
                </div>
                <div
                  className="p-3 rounded"
                  style={{
                    background: "rgba(100,149,237,0.1)",
                    border: "1px solid rgba(100,149,237,0.3)",
                  }}
                >
                  <div
                    className="text-2xl font-display"
                    style={{ color: colors.mana.blue.color }}
                  >
                    {increasedCount}
                  </div>
                  <div className="text-xs" style={{ color: colors.text.muted }}>
                    Existing cards to update
                  </div>
                </div>
              </div>

              <div
                className="text-xs font-display mb-2"
                style={{ color: colors.text.muted }}
              >
                Changes Preview
              </div>
              <div
                className="max-h-64 overflow-auto rounded"
                style={{
                  background: colors.void.light,
                  border: `1px solid ${colors.border.subtle}`,
                }}
              >
                {diff.map((entry, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-3 px-3 py-2"
                    style={{
                      borderBottom:
                        idx < diff.length - 1
                          ? `1px solid ${colors.border.subtle}`
                          : "none",
                      background:
                        entry.change === "added"
                          ? "rgba(0,255,0,0.05)"
                          : "transparent",
                    }}
                  >
                    {/* Change indicator */}
                    <div className="w-16 text-right font-mono text-xs">
                      {entry.change === "added" ? (
                        <span style={{ color: colors.mana.green.color }}>
                          +{entry.newQuantity}
                        </span>
                      ) : (
                        <span style={{ color: colors.mana.blue.color }}>
                          {entry.oldQuantity} → {entry.newQuantity}
                        </span>
                      )}
                    </div>

                    {/* Card info */}
                    <div className="flex-1">
                      <div
                        className="font-display text-sm"
                        style={{ color: colors.text.standard }}
                      >
                        {entry.cardName}
                      </div>
                      {entry.setCode && (
                        <div
                          className="text-xs"
                          style={{ color: colors.text.dim }}
                        >
                          {entry.setCode.toUpperCase()}
                          {entry.collectorNumber &&
                            ` #${entry.collectorNumber}`}
                        </div>
                      )}
                    </div>

                    {/* Badge */}
                    <div
                      className="px-2 py-0.5 rounded text-xs font-display"
                      style={{
                        background:
                          entry.change === "added"
                            ? colors.mana.green.color
                            : colors.mana.blue.color,
                        color: "white",
                      }}
                    >
                      {entry.change === "added" ? "NEW" : "UPDATE"}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {step === "importing" && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <i
                  className="ms ms-c ms-cost animate-spin"
                  style={{ fontSize: "48px", color: colors.gold.standard }}
                />
                <p
                  className="mt-4 font-body"
                  style={{ color: colors.text.muted }}
                >
                  {mode === "replace" ? "Replacing" : "Adding"} {totalCards}{" "}
                  cards...
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="flex items-center justify-between px-5 py-4 border-t"
          style={{ borderColor: colors.border.subtle }}
        >
          <div>
            {(step === "preview" || step === "mode") && (
              <button
                onClick={handleBack}
                className="px-4 py-2 font-display text-sm"
                style={{
                  background: "transparent",
                  color: colors.text.muted,
                  border: `1px solid ${colors.border.standard}`,
                  borderRadius: "3px",
                }}
              >
                Back
              </button>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 font-display text-sm"
              style={{
                background: "transparent",
                color: colors.text.muted,
                border: `1px solid ${colors.border.standard}`,
                borderRadius: "3px",
              }}
            >
              Cancel
            </button>
            {step === "input" && (
              <button
                onClick={handleParse}
                disabled={isLoading || !inputText.trim()}
                className="px-4 py-2 font-display text-sm tracking-wide"
                style={{
                  background:
                    isLoading || !inputText.trim()
                      ? colors.text.muted
                      : colors.gold.standard,
                  color: colors.void.deepest,
                  borderRadius: "3px",
                  opacity: isLoading || !inputText.trim() ? 0.5 : 1,
                }}
              >
                {isLoading ? "Parsing..." : "Parse Cards"}
              </button>
            )}
            {step === "preview" && (
              <button
                onClick={handleImport}
                className="px-4 py-2 font-display text-sm tracking-wide"
                style={{
                  background:
                    mode === "replace"
                      ? colors.mana.red.color
                      : colors.gold.standard,
                  color: "white",
                  borderRadius: "3px",
                }}
              >
                {mode === "replace"
                  ? `Replace with ${totalCards} Cards`
                  : `Add ${totalCards} Cards`}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default CollectionImportModal;
