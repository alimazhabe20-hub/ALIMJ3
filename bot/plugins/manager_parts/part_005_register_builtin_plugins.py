# Auto-split part 5: register_builtin_plugins
def register_builtin_plugins() -> None:
    specs = (
        PluginSpec("ai", "40.x", "AI providers, routing and context", tags=("core", "ai")),
        PluginSpec("weather", "40.x", "Weather and air-quality features", tags=("feature",)),
        PluginSpec("market", "40.x", "Market and crypto features", tags=("feature",)),
        PluginSpec("media", "40.x", "Image, voice and media AI features", tags=("feature", "ai"), dependencies=("ai",)),
        PluginSpec("knowledge", "40.x", "Knowledge base and retrieval", tags=("rag",), dependencies=("ai",)),
        PluginSpec("agents", "40.x", "Workflow, autonomous and multi-agent execution", tags=("agent",), dependencies=("ai", "knowledge")),
        PluginSpec("automation", "40.x", "Scheduled proactive assistant", tags=("automation",)),
    )
    for spec in specs:
        register(spec)
