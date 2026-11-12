#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/desktop/state/ViewState.hpp>
#include <hyprland/src/desktop/state/ViewHitTester.hpp>
#include <hyprland/src/desktop/view/window/Window.hpp>
#include <hyprland/src/desktop/view/window/WindowMetadata.hpp>
#include <hyprland/src/protocols/core/Compositor.hpp>
#include <stdexcept>
#include <vector>

static CFunctionHook* hitHook = nullptr;
using HitFunction = PHLWINDOW (*)(const Desktop::CViewHitTester*, const Vector2D&, uint16_t, PHLWINDOW, PHLWORKSPACE);

static bool isOverlay(const PHLWINDOW& window) {
    const auto& meta = window->metadata();
    return window->backend().isX11() && (meta.appID() == "wispr-flow" || meta.appID() == "Wispr Flow") &&
        (meta.initialTitle() == "Flow Status Indicator" || meta.initialTitle() == "Flow Context Menu");
}

// Only affect this synchronous hit test. Never change keyboard policy, painting,
// window geometry, or the configured no_focus value between input events.
struct Exclusions {
    struct Saved { PHLWINDOW window; bool hadOverride; };
    std::vector<Saved> saved;
    ~Exclusions() {
        for (auto& entry : saved) {
            auto& prop = entry.window->m_ruleApplicator->noFocus();
            if (entry.hadOverride) prop.set(false, Desktop::Types::PRIORITY_SET_PROP);
            else prop.unset(Desktop::Types::PRIORITY_SET_PROP);
        }
    }
};

static PHLWINDOW hitTest(const Desktop::CViewHitTester* tester, const Vector2D& position, uint16_t properties, PHLWINDOW ignored, PHLWORKSPACE workspace) {
    Exclusions exclusions;
    for (const auto& window : Desktop::viewState()->windows()) {
        if (!window->mapped() || !isOverlay(window)) continue;
        const auto surface = window->resource();
        if (!surface) continue;
        const auto local = window->backend().surfaceLocalToBuffer(tester->surfaceLocalAt(position, window, surface));
        if (surface->m_current.effectiveInputRegion().containsPoint(local)) continue;
        auto& prop = window->m_ruleApplicator->noFocus();
        if (prop.valueOrDefault()) continue;
        exclusions.saved.push_back({window, prop.hasValue() && prop.getPriority() == Desktop::Types::PRIORITY_SET_PROP});
        prop.set(true, Desktop::Types::PRIORITY_SET_PROP);
    }
    return reinterpret_cast<HitFunction>(hitHook->m_original)(tester, position, properties, ignored, workspace);
}

APICALL EXPORT std::string PLUGIN_API_VERSION() { return HYPRLAND_API_VERSION; }
APICALL EXPORT PLUGIN_DESCRIPTION_INFO PLUGIN_INIT(HANDLE handle) {
    if (std::string(__hyprland_api_get_hash()) != __hyprland_api_get_client_hash())
        throw std::runtime_error("Wispr input plugin must be rebuilt for the running Hyprland version");
    const auto functions = HyprlandAPI::findFunctionsByName(handle, "windowAtInternal");
    if (functions.size() != 1 || functions[0].demangled.find("Desktop::CViewHitTester::windowAtInternal(") != 0)
        throw std::runtime_error("Unsupported Hyprland hit-test signature");
    hitHook = HyprlandAPI::createFunctionHook(handle, functions[0].address, reinterpret_cast<void*>(&hitTest));
    if (!hitHook || !hitHook->hook()) throw std::runtime_error("Unable to install Wispr input-region hook");
    return {"wispr-input", "Honor Wispr overlay input regions during window selection", "humunkulud", "1.0"};
}
APICALL EXPORT void PLUGIN_EXIT() {}
