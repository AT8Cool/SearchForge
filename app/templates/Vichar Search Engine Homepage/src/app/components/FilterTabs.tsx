import { useState } from 'react';

const tabs = ['All', 'Images', 'News', 'Videos'];

export function FilterTabs() {
  const [activeTab, setActiveTab] = useState('All');

  return (
    <div className="flex gap-6 border-b border-border/40">
      {tabs.map((tab) => (
        <button
          key={tab}
          onClick={() => setActiveTab(tab)}
          className={`
            pb-3 px-2 text-[14px] transition-all relative
            ${activeTab === tab 
              ? 'text-blue-600 dark:text-blue-400' 
              : 'text-muted-foreground hover:text-foreground'
            }
          `}
        >
          {tab}
          {activeTab === tab && (
            <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-blue-600 dark:bg-blue-400 rounded-full" />
          )}
        </button>
      ))}
    </div>
  );
}
