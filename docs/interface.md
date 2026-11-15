# Interface conventions

The product shell has four primary pages: Overview, Research, Journal and Holdings. Secondary research tools belong under More; source configuration and technical status belong in Sources & settings.

Use white surfaces on a neutral background, system typography, fine borders and one muted green accent. Avoid decorative gradients, glowing outlines, emoji navigation, oversized slogans and repeated status badges. Group information by the decision the reader is making.

Overview presents four summary values, sector allocation and upcoming reviews. Scenario planning opens as needed. Journal opens on saved entries; its editor, backup controls, snapshots and revision history are disclosures. Holdings separates import and entry controls from the allocation table. Research uses dated rows with a short excerpt and one reading action.

Keep provenance, historical publication dates, interpretation uncertainty and source access available. Put detailed source excerpts, supporting passages, technical checks and extended reasoning in contextual disclosures. Do not remove material limitations for visual simplicity.

The source settings dialog uses native dialog behavior. The announcement drawer contains keyboard focus, closes with Escape or backdrop click, and restores focus to its opener. Page titles and primary-navigation state follow the selected view. Shared controls retain stable element IDs; the UI contract checks catch missing or duplicate bindings.

The design is implemented in frontend/css/product.css on top of the shared base styles. The profile and study pages load the same product theme. System fonts require no third-party font requests.
