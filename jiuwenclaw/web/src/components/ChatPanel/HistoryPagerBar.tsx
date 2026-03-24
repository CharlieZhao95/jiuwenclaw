import { useTranslation } from 'react-i18next';

export interface HistoryPagerBarProps {
  loadedPages: number;
  totalPages: number;
  loadingMore: boolean;
  onLoadMore: () => void;
}

export function HistoryPagerBar({
  loadedPages,
  totalPages,
  loadingMore,
  onLoadMore,
}: HistoryPagerBarProps) {
  const { t } = useTranslation();
  const hasMore = loadedPages < totalPages;

  return (
    <div className="history-pager-bar mb-3 rounded-lg border border-white/10 bg-secondary/50 px-3 py-2.5 flex flex-wrap items-center justify-between gap-2 text-sm">
      <span className="text-text-muted tabular-nums">
        {t('chat.historyPager.loadedOfTotal', { loaded: loadedPages, total: totalPages })}
      </span>
      {hasMore ? (
        <button
          type="button"
          className="btn !py-1.5 !px-3 text-xs shrink-0"
          disabled={loadingMore}
          onClick={() => {
            void onLoadMore();
          }}
        >
          {loadingMore ? t('chat.historyPager.loadingMore') : t('chat.historyPager.loadMore')}
        </button>
      ) : (
        <span className="text-xs text-text-muted shrink-0">{t('chat.historyPager.allLoaded')}</span>
      )}
    </div>
  );
}
