#%% European football 
#
# Source: https://www.kaggle.com/hugomathien/soccer
# Author: Anders Munk-Nielsen
# 
# Materialize dataset and pick out some variables. 
#
# OUTPUT: 
#   football.csv: one row per team-match pair (i.e. two rows per match). Variables include the betting odds. 
#   football_probs.csv: as above, but with the implied *probabilities* (correcting for the overround). 
# 
import pandas as pd 
import sqlite3
import numpy as np 
import statsmodels.formula.api as smf 

def odds_to_probabilities(dat: pd.core.frame.DataFrame) -> pd.core.frame.DataFrame: 
    '''odds_to_probabilities(): Replaces all the variables relating to odds with the 
            correspondding probabilities implied by those betting odds. Along the way, 
            we correct for the bookmaker "overround", so that 
    '''
    
    # --- 1. convenient shorthand --- 
    # List of the names of all firms that we have betting prices for
    betting_firms = np.unique([c[:-1] for c in dat.columns if c[-1] in ['A', 'H', 'D']])

    # Creating a dictionary that will return all the three price variables for each firm 
    def f_cols(c: str) -> list: 
        # find all columns in dat that start with the prefix, "c" for the first len(c) characters
        # returns the list 
        n = len(c)
        return [col for col in dat.columns if col[:n] == c]

    # dict: firm_vars['B365'] will return ['B365A', 'B365H', 'B365D']
    firm_vars = {c : f_cols(c) for c in betting_firms}

    # find all columns in our dataframe that are *not* betting variables 
    cols_common = [c for c in dat.columns if c[-1] not in ['A', 'H', 'D']]
    cols_common

    # --- 2. initialize output --- 
    d = dat[cols_common].copy()

    # --- 3. primary loop over betting firm names --- 
    for b in betting_firms: 
        # each firm has 3 variables, found in firm_vars[b]
        iodds = 1.0 / dat[firm_vars[b]] # inverse odds (almost probabilities, except for the bookmakers over-round)
        d[b + '_overround'] = iodds.sum(1, skipna=False)

        
        # draw probability (regardless of whether home/away match)
        d[b + '_PrD'] = iodds[b + 'D'] / d[b + '_overround']
        
        d[b + '_PrW'] = np.nan
        d[b + '_PrL'] = np.nan
        
        # home team win/lose probabilities 
        d.loc[d.home, b + '_PrW'] = iodds.loc[d.home, b + 'H'] / d.loc[d.home, b + '_overround']
        d.loc[d.home, b + '_PrL'] = iodds.loc[d.home, b + 'A'] / d.loc[d.home, b + '_overround']
        
        # away team win/lose probabilities 
        d.loc[d.home==False, b + '_PrW'] = iodds.loc[d.home==False, b + 'A'] / d.loc[d.home==False, b + '_overround']
        d.loc[d.home==False, b + '_PrL'] = iodds.loc[d.home==False, b + 'H'] / d.loc[d.home==False, b + '_overround']

    return d 

if __name__ == '__main__': 
    # --- MAIN SCRIPT --- 
    # When executing the script from command line, the code herin will execute. 
    # e.g. 
    # $ python materialize.py 

    #%% Read data 
    # Read sqlite query results into 7 pandas DataFrames 
    print('Materializing football datasets from sqlite source')

    con = sqlite3.connect("./database.sqlite") # open connection to database (file)

    tables = ['Country', 'League', 'Match', 'Player', 'Player_Attributes', 'Team', 'Team_Attributes']

    def get_df(tab: str, con: sqlite3.Connection) -> pd.core.frame.DataFrame: 
        assert tab in tables, f'Table, "{tab}", not in pre-specified list of tables expected to be found in sqlite database.'
        
        df = pd.read_sql_query(f'SELECT * from {tab}', con)

        if ('date' in df.columns) and (df['date'].dtype == 'O'): 
            df['date'] = pd.to_datetime(df['date'])

        return df

    print('Reading sqlite database')
    Match = get_df('Match', con) # a row is a match (with a Home and an Away team)
    Team = get_df('Team', con) # a row is a team 
    Country = get_df('Country', con) # just country names
    League = get_df('League', con) # league names 
    Team_Attributes = get_df('Team_Attributes', con) # from the Fifa game database 

    # Currently, the player information are not used, but they could easily be added
    #Player = get_df('Player', con) # a row is a football player 
    #Player_Attributes = get_df('Player_Attributes', con) # ... same, but for players 

    con.close() # close database connection 
    
    #%% Subsetting columns in the "Match" dataframe 
    # there are many many variables in the underlying dataset, including some that are 
    # basically html code, so we want to subset to get to a smaller dataset. 
    cols_odds = ( # columns relating to betting odds 
        [s for s in Match.columns 
            if ((len(s) == 3) # first two characters = betting firm, 
                & (s[-1] in ['A', 'H', 'D']) # last = A[way], H[ome], D[raw]]
            ) or (
                (len(s) == 5) & (s[:-1] == 'B365') # Bet 365: Away, Home, Draw
            )] 
    )
    common_cols = ['country_id', 'league_id', 'season', 'stage', 'date', 'match_api_id']
    ha_cols = ['home_team_api_id', 'home_team_goal', 'away_team_api_id',  'away_team_goal']
    
    # full list of all kept variables 
    cols = common_cols + ha_cols + cols_odds

    match = Match[cols].copy()

    #%% Wide -> tall 
    # Our goal is to get to a dataframe that has one row per team-match 
    # (i.e. two rows per game). Since all matches have precisely two teams
    # involved per construction, we can just create those two separately. 
    print(f'Transforming from wide to tall')

    # home
    cols = common_cols + ha_cols + cols_odds 
    ren_home = {'home_team_api_id':'team_api_id',       'home_team_goal':'goal', 
                'away_team_api_id':'enemy_team_api_id', 'away_team_goal':'enemy_goal'}
    matches_home = match[cols].rename(columns = ren_home)
    matches_home['home'] = True # all rows here are for the home team 

    # away 
    cols = common_cols + ha_cols + cols_odds 
    ren_away = {'away_team_api_id':'team_api_id', 'away_team_goal':'goal',
                'home_team_api_id':'enemy_team_api_id', 'home_team_goal':'enemy_goal'}
    matches_away = match[cols].rename(columns = ren_away)
    matches_away['home'] = False

    # join 
    m = pd.concat([matches_home, matches_away])
    m['goal_diff'] = m['goal'] - m['enemy_goal']

    #%% Add names 
    print('Adding variables')
    def add_var(M, df_right, id_left: str, id_right: str, var: str, var_new_name: str, DROPIDVARS: bool): 
        '''add_var: From the external df, "tab_right", we take the variable "var" and 
                    add it to the df "M", matching on the id variables (id_left, id_right)
                    (they may have different names in the two dataframes.)
                    Before returning, we rename the added variable from "var" to "rename_var".
        '''
        m = M.copy() # somewhat inefficient this way
        m = pd.merge(m, df_right[[id_right, var]], left_on=id_left, right_on=id_right, how='left').rename(columns = {var: var_new_name})
        if DROPIDVARS: 
            del m[id_left]
            del m[id_right]
        return m 

    m = add_var(m, League,  'league_id',  'id', 'name', 'league', DROPIDVARS=True)
    m = add_var(m, Country, 'country_id', 'id', 'name', 'country', DROPIDVARS=True)
    m = add_var(m, Team,    'team_api_id', 'team_api_id', 'team_long_name', 'team', DROPIDVARS=False)

    # add enemy team name 
    # (done separately because otherwise we get two "team_api_id" columns...)
    ren = {'team_api_id':'enemy_team_api_id', 'team_long_name':'enemy_team'}
    t = Team[['team_api_id', 'team_long_name']].rename(columns=ren)
    m = pd.merge(m, t, on='enemy_team_api_id', how='left') 

    cols_to_cat = ['league', 'season', 'team', 'country']
    for c in cols_to_cat: 
        m[c] = m[c].astype('category')

    # reorder cols 
    cols_not_odds = [c for c in m.columns if c not in cols_odds]
    m = m.loc[:, cols_not_odds + cols_odds]

    # %% Export data into a more useful format 
    print('Exporting')
    m.to_csv('football.csv', index=False)

    Team.to_csv('team_info.csv', index=False)

    print(f'Done, exported "football.csv" ({m.shape[0]:,d} rows) and "team_info.csv" ({Team.shape[0]}) rows)')

    #%% Just a quick regression 
    print(f'Printing a quick, illustrious regression: y=goal, x=1(home)')
    r = smf.ols('goal ~ home + country + league + season + C(stage)', m).fit()
    tab = pd.DataFrame([r.params, r.bse], index=['Beta', 'SE']).T.loc['home[T.True]', :].to_frame('1(home)')
    print(tab)

    #%% From odds to probabilities 
    print('Converting odds to probabilities')
    d = odds_to_probabilities(m)
    d.to_csv('football_probs.csv', index=False)
    print(f'Wrote "football_probs.csv" with shape={d.shape}')


