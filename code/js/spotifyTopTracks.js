// Authorization token that must have been created previously. See : https://developer.spotify.com/documentation/web-api/concepts/authorization
const token = 'BQBf4pdtXLfSPgyvVzlE5WL56tPPlTWzARxI6EFcxyc6E32L3rNYbpEEXBDN-s8ow8TfeoO7PoFE6E5JKAtSaX-9yAL2jt4YSgUaoO5Sn-CCVnW8SNh-3Bgm0FGJkEEMzZjNkd91ZoI7zRZ7tHIagJkEgr8ZaZbhQzkSy2QZeXvQk9qceE0bydiWjokeFnqvy8XL68rZG6fJv-_4_b_e3XYnz8k60tw0YSMEwNWgsUjB5189uiuoPkW1pp4kEoyieaECRAa5dsWvxdn_xvDj8wGH8ObXT2WHPkonRbPg0lNQH7O29qNOGDZ0rpvhKXwc'; // Replace with valid token

async function fetchWebApi(endpoint, method, body) {
  const res = await fetch(`https://api.spotify.com/${endpoint}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    method,
    body: body ? JSON.stringify(body) : undefined
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(`Spotify API error: ${res.status} ${res.statusText} - ${JSON.stringify(err)}`);
  }

  return await res.json();
}

async function getTopTracks() {
  const data = await fetchWebApi(
    'v1/me/top/tracks?time_range=long_term&limit=5', 'GET'
  );
  return data.items;
}

async function createPlaylistFromTopTracks() {
  const topTracks = await getTopTracks();
  const trackUris = topTracks.map(track => track.uri);

  const { id: user_id } = await fetchWebApi('v1/me', 'GET');

  const playlist = await fetchWebApi(
    `v1/users/${user_id}/playlists`, 'POST', {
      name: "My Top Tracks Playlist",
      description: "Playlist created from user's top tracks",
      public: false
    }
  );

  await fetchWebApi(
    `v1/playlists/${playlist.id}/tracks?uris=${trackUris.join(',')}`,
    'POST'
  );

  console.log(`Created playlist: ${playlist.name} (${playlist.id})`);
  return playlist;
}

// Run the main function
createPlaylistFromTopTracks().catch(console.error);