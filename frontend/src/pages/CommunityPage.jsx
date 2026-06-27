import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  getCommunityPosts,
  getCommunityPost,
  postCommunityPost,
  togglePostUpvote,
  postPostReply,
  generatePostAiAnswer,
  getFarmerProfile,
} from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { useToast } from '../contexts/ToastContext';
import { Spinner, Skeleton, EmptyState } from '../components/shared/LoadingStates';
import {
  COMMON_CROPS,
  DISTRICTS,
  getCropEmoji,
  toBengaliNumerals,
  formatRelativeTimeBn,
} from '../utils/farmOptions';

const CK = 'community';

// The four crops that get dedicated chips, plus an "Other" bucket — must match
// the backend NAMED_CROPS list in community_service.py.
const CROP_CHIPS = ['ধান', 'গম', 'আলু', 'পাট', 'অন্যান্য'];

/**
 * Derive a stable, recognizable-but-anonymous handle from the hashed farmer id.
 * Posts only ever carry farmer_id_hashed (deliberately anonymized); this turns
 * that opaque hash into a consistent "কৃষক ৪৩৭"-style label so the feed still
 * feels human and trustworthy without exposing the real username.
 */
function farmerHandle(farmerIdHashed, t) {
  if (!farmerIdHashed) return `${t(`${CK}.farmer_prefix`)} ?`;
  // Stable number from the trailing part of the id (a UUID hex tail).
  const tail = String(farmerIdHashed).replace(/[^0-9a-f]/gi, '').slice(-6);
  const num = parseInt(tail, 16) % 900 + 100; // 100–999
  return `${t(`${CK}.farmer_prefix`)} ${toBengaliNumerals(num)}`;
}

export default function CommunityPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState('browse'); // 'browse' | 'ask'

  return (
    <div className="space-y-4">
      {/* Tab switcher */}
      <div className="flex gap-2">
        {[['browse', `💬 ${t(`${CK}.tab_browse`)}`], ['ask', `✍️ ${t(`${CK}.tab_ask`)}`]].map(
          ([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex-1 py-2.5 rounded-btn text-xs sm:text-sm font-medium transition-all whitespace-nowrap
                ${tab === key
                  ? 'bg-primary text-white shadow-card'
                  : 'bg-surface border border-border text-text-secondary hover:border-primary'}`}
            >
              {label}
            </button>
          )
        )}
      </div>

      {tab === 'browse' && <BrowseTab />}
      {tab === 'ask' && <AskTab onDone={() => setTab('browse')} />}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Crop filter chip                                                    */
/* ------------------------------------------------------------------ */

function CropChip({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`shrink-0 px-3 py-1.5 rounded-pill text-sm font-medium border transition-all
        ${active
          ? 'bg-primary text-white border-primary shadow-card'
          : 'bg-surface text-text-primary border-border hover:border-primary'}`}
    >
      {children}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* District combobox (text input + dropdown)                           */
/* ------------------------------------------------------------------ */

function DistrictPicker({ value, onChange, placeholder }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value || '');
  const ref = useRef(null);

  useEffect(() => setQuery(value || ''), [value]);

  // Close the dropdown on outside click.
  useEffect(() => {
    function onDocClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  const filtered = DISTRICTS.filter((d) =>
    d.toLowerCase().includes((query || '').toLowerCase())
  );

  const pick = (d) => {
    onChange(d);
    setQuery(d);
    setOpen(false);
  };

  const clear = () => {
    onChange('');
    setQuery('');
  };

  return (
    <div className="relative flex-1" ref={ref}>
      <input
        value={query}
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          // If the typed text matches a district exactly, propagate it; otherwise
          // treat a partial/empty value as no filter until the user picks one.
          if (DISTRICTS.includes(e.target.value)) onChange(e.target.value);
          else if (!e.target.value) onChange('');
        }}
        placeholder={`📍 ${placeholder}`}
        className="input-field !py-2 pr-8"
      />
      {query && (
        <button
          onClick={clear}
          className="absolute right-2 top-1/2 -translate-y-1/2 w-6 h-6 flex items-center justify-center
                     text-text-secondary hover:text-text-primary rounded-full"
          aria-label="clear"
        >
          ✕
        </button>
      )}
      {open && filtered.length > 0 && (
        <div className="absolute z-30 mt-1 w-full max-h-60 overflow-auto bg-surface rounded-btn shadow-elevated border border-border">
          {filtered.map((d) => (
            <button
              key={d}
              onClick={() => pick(d)}
              className="w-full text-left px-4 py-2.5 text-sm hover:bg-bg transition-colors text-text-primary"
            >
              📍 {d}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* BROWSE TAB                                                          */
/* ------------------------------------------------------------------ */

function BrowseTab() {
  const { t } = useTranslation();
  const [crop, setCrop] = useState(''); // '' => "all"
  const [sort, setSort] = useState('new');
  const [district, setDistrict] = useState('');

  const [posts, setPosts] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState(null); // opens the detail sheet
  const reqId = useRef(0);

  const fetchPage = useCallback(
    async (pageNum, append) => {
      const id = ++reqId.current;
      if (append) setLoadingMore(true);
      else {
        setLoading(true);
        setError('');
      }
      try {
        const data = await getCommunityPosts({
          district: district || undefined,
          crop: crop || undefined,
          sort,
          page: pageNum,
        });
        if (id !== reqId.current) return; // a newer request superseded this one
        const next = data.posts || [];
        setPosts((prev) => (append ? [...prev, ...next] : next));
        setPage(pageNum);
        setHasMore(!!data.has_more);
      } catch (e) {
        if (id !== reqId.current) return;
        setError(e.message || t(`${CK}.failed`));
      } finally {
        if (id === reqId.current) {
          setLoading(false);
          setLoadingMore(false);
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [crop, sort, district]
  );

  // Initial / refetch on filter change.
  useEffect(() => {
    fetchPage(1, false);
  }, [fetchPage]);

  return (
    <div className="space-y-3">
      {/* Sticky filter bar */}
      <div className="sticky top-[52px] z-20 -mx-4 px-4 py-3 bg-bg/95 backdrop-blur-sm border-b border-border space-y-2">
        {/* Crop chips (horizontal scroll) */}
        <div className="flex gap-2 overflow-x-auto pb-1 -mb-1" style={{ scrollbarWidth: 'none' }}>
          <CropChip active={crop === ''} onClick={() => setCrop('')}>
            🌱 {t(`${CK}.filter_all_crops`)}
          </CropChip>
          {CROP_CHIPS.map((c) => (
            <CropChip key={c} active={crop === c} onClick={() => setCrop(c)}>
              {getCropEmoji(c)} {c}
            </CropChip>
          ))}
        </div>

        {/* Sort + district */}
        <div className="flex gap-2 items-center">
          <div className="flex gap-1 shrink-0">
            {[
              ['new', `🕒 ${t(`${CK}.sort_new`)}`],
              ['top', `🔥 ${t(`${CK}.sort_top`)}`],
            ].map(([key, label]) => (
              <button
                key={key}
                onClick={() => setSort(key)}
                className={`px-3 py-2 rounded-btn text-xs font-medium border transition-all whitespace-nowrap
                  ${sort === key
                    ? 'bg-primary text-white border-primary'
                    : 'bg-surface text-text-secondary border-border hover:border-primary'}`}
              >
                {label}
              </button>
            ))}
          </div>
          <DistrictPicker
            value={district}
            onChange={setDistrict}
            placeholder={t(`${CK}.district_placeholder`)}
          />
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-danger-light text-danger p-3 rounded-card text-sm text-center font-medium">
          ⚠️ {error}
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card">
              <Skeleton lines={3} />
            </div>
          ))}
        </div>
      ) : posts.length > 0 ? (
        <>
          <div className="space-y-3">
            {posts.map((p) => (
              <PostCard key={p.id} post={p} onOpen={() => setSelectedId(p.id)} />
            ))}
          </div>
          {hasMore && (
            <button
              onClick={() => fetchPage(page + 1, true)}
              disabled={loadingMore}
              className="btn-outline w-full !py-2.5 flex items-center justify-center gap-2"
            >
              {loadingMore ? <Spinner size="sm" /> : null}
              {loadingMore ? t('common.loading') : t(`${CK}.load_more`)}
            </button>
          )}
        </>
      ) : (
        <EmptyState
          icon="💬"
          title={t(`${CK}.no_posts`)}
          message={t(`${CK}.no_posts_msg`)}
        />
      )}

      {/* Detail bottom sheet */}
      {selectedId && (
        <PostSheet postId={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Post card (list item)                                               */
/* ------------------------------------------------------------------ */

function PostCard({ post, onOpen }) {
  const { t } = useTranslation();
  const preview = (post.question_text || '').slice(0, 160);

  return (
    <button
      onClick={onOpen}
      className="card w-full text-left space-y-3 hover:shadow-elevated transition-shadow"
    >
      {/* Header: avatar + name + district badge */}
      <div className="flex items-center gap-2">
        <span className="w-9 h-9 shrink-0 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center">
          {(farmerHandle(post.farmer_id_hashed, t).slice(-1) || '?')}
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-bold text-text-primary text-sm leading-tight truncate">
            {farmerHandle(post.farmer_id_hashed, t)}
          </p>
          {post.district && (
            <p className="text-xs text-text-secondary">📍 {post.district}</p>
          )}
        </div>
        {post.ai_answer && (
          <span className="badge-success text-[10px] whitespace-nowrap shrink-0">
            {t(`${CK}.ai_badge`)}
          </span>
        )}
      </div>

      {/* Preview text (2–3 lines) */}
      <p className="text-sm text-text-primary line-clamp-3 whitespace-pre-wrap">{preview}</p>

      {/* Crop tag */}
      <div className="flex items-center gap-2">
        <span className="badge-warning text-xs">
          {getCropEmoji(post.crop_type)} {post.crop_type || '—'}
        </span>
      </div>

      {/* Bottom row: upvote / replies / time */}
      <div className="flex items-center gap-4 text-xs text-text-secondary pt-1 border-t border-border">
        <span className="flex items-center gap-1">
          ▲ {toBengaliNumerals(post.upvotes_count || 0)}
        </span>
        <span className="flex items-center gap-1">
          💬 {toBengaliNumerals(post.answers_count || 0)}
        </span>
        {post.created_at && (
          <span className="ml-auto">{formatRelativeTimeBn(post.created_at)}</span>
        )}
      </div>
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* Full post view (bottom sheet)                                       */
/* ------------------------------------------------------------------ */

function PostSheet({ postId, onClose }) {
  const { t } = useTranslation();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [voting, setVoting] = useState(false);
  const [replyText, setReplyText] = useState('');
  const [replying, setReplying] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    getCommunityPost(postId)
      .then((data) => alive && setPost(data))
      .catch((e) => alive && setError(e.message || 'Error'))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [postId]);

  // Lock body scroll while the sheet is open.
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, []);

  const handleUpvote = async () => {
    if (!post || voting) return;
    setVoting(true);
    // Optimistic toggle for a snappy feel.
    const wasUpvoted = !!post.upvoted_by_me;
    setPost((p) => ({
      ...p,
      upvoted_by_me: !wasUpvoted,
      upvotes_count: (p.upvotes_count || 0) + (wasUpvoted ? -1 : 1),
    }));
    try {
      const res = await togglePostUpvote(postId);
      setPost((p) => ({ ...p, upvoted_by_me: res.upvoted, upvotes_count: res.upvotes_count }));
    } catch {
      // Roll back on failure.
      setPost((p) => ({
        ...p,
        upvoted_by_me: wasUpvoted,
        upvotes_count: (p.upvotes_count || 0) + (wasUpvoted ? 1 : -1),
      }));
    } finally {
      setVoting(false);
    }
  };

  const handleReply = async () => {
    if (!replyText.trim() || replying) return;
    setReplying(true);
    try {
      await postPostReply(postId, replyText.trim());
      // Refresh to pick up the new answer + bumped count.
      const fresh = await getCommunityPost(postId);
      setPost(fresh);
      setReplyText('');
    } catch (e) {
      setError(e.message || t(`${CK}.failed`));
    } finally {
      setReplying(false);
    }
  };

  const handleAiAnswer = async () => {
    if (aiBusy) return;
    setAiBusy(true);
    try {
      const res = await generatePostAiAnswer(postId);
      setPost((p) => ({ ...p, ai_answer: res.ai_answer, ...res.post }));
    } catch (e) {
      // 429 = rate limited (already generated this hour); other = transient.
      if (e.status === 429) {
        setError(t(`${CK}.ai_cooldown`));
      } else {
        setError(t(`${CK}.ai_failed`));
      }
    } finally {
      setAiBusy(false);
    }
  };

  const answers = post?.answers || [];

  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Sheet */}
      <div className="relative w-full max-w-2xl bg-bg rounded-t-card shadow-elevated max-h-[92vh] flex flex-col animate-[slideUp_0.25s_ease]">
        {/* Drag handle + close */}
        <div className="flex items-center justify-center pt-2 pb-1 shrink-0">
          <div className="w-10 h-1.5 rounded-full bg-border" />
        </div>
        <div className="flex items-center justify-between px-4 pb-2 shrink-0">
          <h3 className="font-bold text-text-primary">{t('nav.community')}</h3>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-surface border border-border text-text-secondary hover:text-text-primary"
            aria-label={t(`${CK}.close`)}
          >
            ✕
          </button>
        </div>

        {/* Scrollable content */}
        <div className="overflow-y-auto px-4 pb-4 space-y-3">
          {loading ? (
            <div className="card"><Skeleton lines={5} /></div>
          ) : error && !post ? (
            <div className="bg-danger-light text-danger p-3 rounded-card text-sm text-center">{error}</div>
          ) : post ? (
            <>
              {/* Full post */}
              <div className="card space-y-3">
                <div className="flex items-center gap-2">
                  <span className="w-10 h-10 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center">
                    {(farmerHandle(post.farmer_id_hashed, t).slice(-1) || '?')}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-bold text-text-primary text-sm leading-tight">
                      {farmerHandle(post.farmer_id_hashed, t)}
                    </p>
                    <p className="text-xs text-text-secondary">
                      {post.district ? `📍 ${post.district}` : ''}{' '}
                      {post.created_at && `· ${formatRelativeTimeBn(post.created_at)}`}
                    </p>
                  </div>
                </div>
                <p className="text-text-primary whitespace-pre-wrap">{post.question_text}</p>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="badge-warning text-xs">
                    {getCropEmoji(post.crop_type)} {post.crop_type || '—'}
                  </span>
                  {post.ai_answer && (
                    <span className="badge-success text-xs">{t(`${CK}.ai_badge`)}</span>
                  )}
                </div>
                {/* Upvote action */}
                <div className="flex items-center gap-3 pt-2 border-t border-border">
                  <button
                    onClick={handleUpvote}
                    disabled={voting}
                    className={`px-3 py-1.5 rounded-pill text-sm font-medium border transition-all flex items-center gap-1
                      ${post.upvoted_by_me
                        ? 'bg-primary text-white border-primary'
                        : 'bg-surface text-text-primary border-border hover:border-primary'}`}
                  >
                    ▲ {toBengaliNumerals(post.upvotes_count || 0)}
                  </button>
                  <span className="text-xs text-text-secondary">
                    💬 {toBengaliNumerals(post.answers_count || 0)} {t(`${CK}.replies`)}
                  </span>
                </div>
              </div>

              {/* AI answer card */}
              {post.ai_answer ? (
                <div className="rounded-card border-2 border-primary/40 bg-primary/5 p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">🤖</span>
                    <span className="font-bold text-primary text-sm">{t(`${CK}.ai_label`)}</span>
                  </div>
                  <p className="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
                    {post.ai_answer}
                  </p>
                </div>
              ) : aiBusy ? (
                <div className="rounded-card border-2 border-primary/40 bg-primary/5 p-4 flex items-center gap-3">
                  <Spinner size="sm" className="text-primary" />
                  <span className="text-sm text-primary font-medium">{t(`${CK}.ai_generating`)}</span>
                </div>
              ) : (
                <button
                  onClick={handleAiAnswer}
                  className="btn-outline w-full !py-2.5 text-sm"
                >
                  {t(`${CK}.ai_generate`)}
                </button>
              )}

              {error && (
                <div className="bg-danger-light text-danger p-2 rounded-btn text-xs text-center">
                  {error}
                </div>
              )}

              {/* Human replies */}
              <div className="space-y-2">
                <h4 className="text-sm font-bold text-text-primary">
                  💬 {answers.length > 0
                    ? `${toBengaliNumerals(answers.length)} ${t(`${CK}.replies`)}`
                    : t(`${CK}.replies_none`)}
                </h4>
                {answers.map((a) => (
                  <div key={a.id} className="card !p-3 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="w-7 h-7 rounded-full bg-accent-light/40 text-soil font-bold text-xs flex items-center justify-center">
                        {(a.answerer_name || '?').charAt(0).toUpperCase()}
                      </span>
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-text-primary leading-tight">
                          {a.answerer_name}
                          {a.is_expert_answer && (
                            <span className="ml-1 badge-success text-[10px] !px-2 !py-0.5">✓</span>
                          )}
                        </p>
                        {a.created_at && (
                          <p className="text-[10px] text-text-secondary">
                            {formatRelativeTimeBn(a.created_at)}
                          </p>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-text-primary whitespace-pre-wrap pl-9">{a.answer_text}</p>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </div>

        {/* Reply input (fixed at sheet bottom) */}
        <div className="shrink-0 border-t border-border bg-surface p-3 flex gap-2"
             style={{ paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 0.75rem)' }}>
          <input
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleReply()}
            placeholder={t(`${CK}.reply_placeholder`)}
            className="input-field flex-1 !py-2"
          />
          <button
            onClick={handleReply}
            disabled={!replyText.trim() || replying}
            className="btn-primary !py-2 !px-4 flex items-center gap-1"
          >
            {replying ? <Spinner size="sm" /> : '➤'} {t(`${CK}.reply_send`)}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* ASK TAB                                                             */
/* ------------------------------------------------------------------ */

function AskTab({ onDone }) {
  const { t } = useTranslation();
  const toast = useToast();
  const { lat, lon } = useGeolocation();

  const [text, setText] = useState('');
  const [crop, setCrop] = useState(COMMON_CROPS[0]);
  const [district, setDistrict] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Prefill district from the farmer profile (editable).
  useEffect(() => {
    const ctrl = new AbortController();
    getFarmerProfile(ctrl.signal)
      .then((p) => {
        if (p && p.district) setDistrict(p.district);
      })
      .catch(() => {});
    return () => ctrl.abort();
  }, []);

  const handleSubmit = async () => {
    if (!text.trim() || submitting) return;
    setSubmitting(true);
    setError('');
    try {
      const created = await postCommunityPost({
        question_text: text.trim(),
        crop_type: crop,
        growth_stage: null,
        lat: lat ?? undefined,
        lon: lon ?? undefined,
        district: district || undefined,
      });
      toast.show(t(`${CK}.success`));

      // Auto-trigger AI answer generation in the background. We don't block the
      // navigation on this; the user will see it when they open the post.
      const newId = created?.id;
      if (newId) {
        generatePostAiAnswer(newId).catch(() => {
          // Non-fatal: the post is created; AI can be requested later.
        });
      }

      setText('');
      onDone();
    } catch (e) {
      setError(e.message || t(`${CK}.failed`));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card-elevated space-y-4">
      {/* Question textarea */}
      <div className="space-y-1.5">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t(`${CK}.ask_placeholder`)}
          rows={5}
          className="input-field min-h-[120px] resize-y"
        />
      </div>

      {/* Crop selector chips */}
      <div className="space-y-1.5">
        <p className="text-xs font-semibold text-text-secondary">{t(`${CK}.ask_crop_hint`)}</p>
        <div className="flex flex-wrap gap-2">
          {COMMON_CROPS.map((c) => (
            <CropChip key={c} active={crop === c} onClick={() => setCrop(c)}>
              {getCropEmoji(c)} {c}
            </CropChip>
          ))}
        </div>
      </div>

      {/* District (from profile, editable) */}
      <div className="space-y-1.5">
        <p className="text-xs font-semibold text-text-secondary">{t(`${CK}.ask_district`)}</p>
        <DistrictPicker
          value={district}
          onChange={setDistrict}
          placeholder={t(`${CK}.district_placeholder`)}
        />
      </div>

      {error && (
        <div className="bg-danger-light text-danger p-3 rounded-btn text-sm text-center font-medium">
          ⚠️ {error}
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!text.trim() || submitting}
        className="btn-primary w-full flex items-center justify-center gap-2"
      >
        {submitting ? <Spinner size="sm" /> : '✍️'}{' '}
        {submitting ? t(`${CK}.posting`) : t(`${CK}.submit`)}
      </button>

      <p className="text-xs text-text-secondary text-center">
        🤖 {t(`${CK}.ai_generating`)}
      </p>
    </div>
  );
}
