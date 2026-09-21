using Microsoft.UI.Dispatching;
using Microsoft.UI.Xaml;
using Microsoft.Windows.AppLifecycle;

namespace SmartSearch.Desktop;

public static class Program
{
    private const string InstanceKey = "SmartSearch.Desktop";
    internal const string MutexName = @"Local\SmartSearch.Desktop";

    [STAThread]
    public static void Main(string[] args)
    {
        WinRT.ComWrappersSupport.InitializeComWrappers();
        var current = AppInstance.GetCurrent();
        var main = AppInstance.FindOrRegisterForKey(InstanceKey);
        if (!main.IsCurrent)
        {
            // Keep the real entry point synchronous so the CLR honors STAThread.
            Task.Run(async () => await main.RedirectActivationToAsync(current.GetActivatedEventArgs()))
                .GetAwaiter().GetResult();
            return;
        }

        // Hold an open named handle for the installer without taking mutex ownership.
        var mutex = new Mutex(initiallyOwned: false, MutexName);
        App.SetSingleInstance(mutex, main);
        Application.Start(_ =>
        {
            SynchronizationContext.SetSynchronizationContext(
                new DispatcherQueueSynchronizationContext(DispatcherQueue.GetForCurrentThread()));
            new App();
        });
    }
}
