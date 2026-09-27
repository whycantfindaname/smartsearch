using SmartSearch.Desktop;

Localization.Preference = "zh";
if (ActivityPresentation.ProviderModel("firecrawl", "") != "服务商：firecrawl" ||
    ActivityPresentation.ProviderModel("openai-compatible", "grok-test") != "服务商：openai-compatible · 模型：grok-test" ||
    ActivityPresentation.ProviderModel("", "") != "")
    throw new Exception("Activity captions must distinguish a model from a non-model provider.");

// The same real client must reconnect after stopping for a failed installer
// launch. No UI, installer, package manager, or provider is invoked here.
if (args.Length != 2) throw new ArgumentException("Pass Python executable and an isolated config directory.");
await using var client = new BackendClient(args[0], ["-m", "smart_search.desktop_entry"]);
for (var attempt = 0; attempt < 2; attempt++)
{
    var state = await client.StartAsync(args[1], CancellationToken.None);
    if (state.GetProperty("protocol_version").GetInt32() != 1) throw new Exception("Handshake failed.");
    var pong = await client.CallAsync("ping", new { }, CancellationToken.None);
    if (pong.GetProperty("protocol_version").GetInt32() != 1) throw new Exception("Reconnect failed.");
    await client.StopAsync();
    if (client.IsConnected) throw new Exception("Stopped backend is still connected.");
}
Console.WriteLine("PASS: stop and reconnect preserve the private RPC client.");
