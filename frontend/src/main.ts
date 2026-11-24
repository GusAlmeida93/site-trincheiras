import './styles/main.css';
import 'leaflet/dist/leaflet.css';

import { getLessonBundle } from './api/client';
import { initClauses } from './features/clauses';
import { initEnlistment } from './features/enlistment';
import { initFlipCards } from './features/flip-cards';
import { createMapSection } from './features/map';
import { initParticipants } from './features/participants';
import { initTabs } from './features/tabs';
import { initTrench } from './features/trench';
import { initWarRoom } from './features/war-room';

// Every initializer no-ops when its root element is absent, so the modules
// stay independent of which sections a lesson page actually renders.
initFlipCards();
initEnlistment();
initParticipants();
initClauses();

const mapSection = createMapSection();

initTabs({
  onActivate: (targetId) => {
    if (targetId === 'mapa') {
      mapSection.onPanelShown();
    }
  },
});

const lessonSlug = document.documentElement.dataset.lessonSlug ?? 'tratado-de-versalhes';

void (async () => {
  const bundle = await getLessonBundle(lessonSlug);
  if (!bundle) {
    mapSection.showFallback();
    return;
  }

  mapSection.setRegions(bundle.map_regions);

  const warRoom = bundle.activities.find((activity) => activity.kind === 'match');
  if (warRoom) {
    initWarRoom(warRoom);
  }

  const trench = bundle.activities.find((activity) => activity.kind === 'quiz');
  if (trench) {
    initTrench(trench);
  }
})();
